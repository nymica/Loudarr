import re
import time
from collections import Counter
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for

import database as db
from lidarr import LidarrClient
from discovery import DiscoveryEngine

app = Flask(__name__)
db.init_db()


def get_lidarr():
    cfg = db.get_config()
    url = cfg.get('lidarr_url', '')
    key = cfg.get('lidarr_api_key', '')
    if not url or not key:
        return None
    return LidarrClient(url, key)


def get_discovery():
    cfg = db.get_config()
    enabled = ['lastfm']
    if cfg.get('source_musicbrainz', '1') == '1':
        enabled.append('musicbrainz')
    if cfg.get('source_deezer', '1') == '1':
        enabled.append('deezer')
    if cfg.get('source_listenbrainz', '1') == '1':
        enabled.append('listenbrainz')
    return DiscoveryEngine(
        lastfm_api_key=cfg.get('lastfm_api_key', '') or None,
        enabled_sources=enabled,
    )


def is_configured():
    cfg = db.get_config()
    return bool(cfg.get('lidarr_url') and cfg.get('lidarr_api_key'))


def _normalize_name(name):
    """Lowercase, strip leading 'the', remove punctuation — for fuzzy name comparison."""
    s = name.lower().strip()
    s = re.sub(r'^the\s+', '', s)
    s = re.sub(r'[^\w\s]', '', s)
    return ' '.join(s.split())


def _tags_match_genre(genre, tags):
    """True when any artist tag shares a word with the searched genre string."""
    if not tags:
        return True  # no tags available — allow through
    genre_words = set(genre.lower().replace('-', ' ').replace('/', ' ').split())
    for tag in tags:
        tag_words = set(tag.lower().replace('-', ' ').replace('/', ' ').split())
        if genre_words & tag_words:
            return True
    return False


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if not is_configured():
        return redirect(url_for('settings'))
    return render_template('discover.html', active='discover')


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    error = None
    success = None
    if request.method == 'POST':
        db.set_config('lidarr_url',      request.form.get('lidarr_url', '').strip().rstrip('/'))
        db.set_config('lidarr_api_key',  request.form.get('lidarr_api_key', '').strip())
        db.set_config('lastfm_api_key',  request.form.get('lastfm_api_key', '').strip())
        db.set_config('min_listeners',   request.form.get('min_listeners', '10000').strip())
        db.set_config('extra_genres',    request.form.get('extra_genres', '').strip())
        db.set_config('source_musicbrainz',  '1' if 'source_musicbrainz'  in request.form else '0')
        db.set_config('source_deezer',       '1' if 'source_deezer'       in request.form else '0')
        db.set_config('source_listenbrainz', '1' if 'source_listenbrainz' in request.form else '0')
        success = 'Settings saved.'

    cfg = db.get_config()
    return render_template('settings.html', active='settings', config=cfg,
                           error=error, success=success)


@app.route('/ignored')
def ignored():
    return render_template('ignored.html', active='ignored', artists=db.get_ignored_artists())


@app.route('/history')
def history():
    return render_template('history.html', active='history', artists=db.get_added_artists())


# ── API ───────────────────────────────────────────────────────────────────────

@app.route('/api/test-connection', methods=['POST'])
def api_test_connection():
    data = request.json or {}
    url = data.get('url', '').strip().rstrip('/')
    key = data.get('api_key', '').strip()
    if not url or not key:
        return jsonify({'ok': False, 'error': 'URL and API key are required'})
    ok, error = LidarrClient(url, key).test_connection()
    return jsonify({'ok': ok, 'error': error})


@app.route('/api/taxonomy')
def api_taxonomy():
    from taxonomy import annotate_with_library

    cached = db.get_cached('taxonomy_annotated', ttl_hours=6)
    if cached:
        return jsonify(cached)

    library_genres = []
    lidarr = get_lidarr()
    if lidarr:
        try:
            artists = lidarr.get_artists()
            for a in artists:
                library_genres.extend(a.get('genres', []))
        except Exception:
            pass

    result = annotate_with_library(library_genres)
    db.set_cached('taxonomy_annotated', result)
    return jsonify(result)


@app.route('/api/genres')
def api_genres():
    lidarr = get_lidarr()
    if not lidarr:
        return jsonify({'error': 'Lidarr not configured'}), 400

    cached = db.get_cached('library_genres', ttl_hours=6)
    if cached:
        return jsonify(cached)

    try:
        artists = lidarr.get_artists()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    counts = Counter()
    for a in artists:
        for g in a.get('genres', []):
            counts[g.lower().strip()] += 1

    cfg = db.get_config()
    for g in cfg.get('extra_genres', '').split(','):
        g = g.strip().lower()
        if g and g not in counts:
            counts[g] = 0

    result = [{'genre': g, 'count': c} for g, c in counts.most_common(40) if g]
    db.set_cached('library_genres', result)
    return jsonify(result)


@app.route('/api/discover')
def api_discover():
    mode   = request.args.get('mode', 'genre')
    genre  = request.args.get('genre', '').strip()
    range_ = request.args.get('range', 'month')
    page   = max(1, int(request.args.get('page', 1)))
    per_page = 25

    lidarr = get_lidarr()
    if not lidarr:
        return jsonify({'error': 'Lidarr not configured'}), 400

    cfg = db.get_config()
    min_listeners = int(cfg.get('min_listeners', 10000) or 10000)

    try:
        library_artists = lidarr.get_artists()
    except Exception as e:
        return jsonify({'error': f'Lidarr error: {e}'}), 500

    library_names = {a['artistName'].lower() for a in library_artists}
    ignored_names = {a['artist_name'].lower() for a in db.get_ignored_artists()}
    added_names   = {a['artist_name'].lower() for a in db.get_added_artists()}
    excluded = library_names | ignored_names | added_names

    discovery = get_discovery()

    # ── Genre ────────────────────────────────────────────────────────────────
    if mode == 'genre':
        if not genre:
            return jsonify({'error': 'Genre is required'}), 400
        if not discovery.any_genre_source():
            return jsonify({'error': 'No discovery sources are enabled — check Settings.'}), 400

        cache_key  = f'discover_genre:{genre}:{min_listeners}'
        suggestions = db.get_cached(cache_key, ttl_hours=24)

        if suggestions is None:
            raw = discovery.get_artists_by_tag(genre, limit=100)
            suggestions = []
            for a in raw:
                if a['name'].lower() in excluded:
                    continue
                info = discovery.get_artist_info(a['name'])
                listeners = info.get('listeners') if info else a.get('listeners')

                # Apply min_listeners only when we have a real count
                if listeners is not None and listeners < min_listeners:
                    continue

                # Drop artists whose tags don't relate to the searched genre.
                # This catches popular artists with many diverse tags that slip through
                # source-level searches (e.g. appearing in metal *and* jazz results).
                all_tags = (info.get('tags') if info else None) or a.get('tags', [])
                if not _tags_match_genre(genre, all_tags):
                    continue

                suggestions.append({
                    'name':      a['name'],
                    'mbid':      a.get('mbid') or info.get('mbid', ''),
                    'listeners': listeners,
                    'tags':      info.get('tags') or a.get('tags', []),
                    'bio':       info.get('bio', ''),
                    'image':     info.get('image') or a.get('image', ''),
                    'url':       info.get('url')  or a.get('url', ''),
                    'genre':     genre,
                    'based_on':  '',
                    'source':    info.get('source') or a.get('source', ''),
                })
                if info:
                    time.sleep(0.1)

            suggestions.sort(key=lambda x: (x['listeners'] or 0), reverse=True)
            db.set_cached(cache_key, suggestions)

    # ── Similar ──────────────────────────────────────────────────────────────
    elif mode == 'similar':
        if not discovery.lastfm:
            return jsonify({'error': 'Similar artist discovery requires a Last.fm API key — add one in Settings, or try By Genre or Trending.'}), 400

        cache_key   = f'discover_similar:{min_listeners}'
        suggestions = db.get_cached(cache_key, ttl_hours=12)

        if suggestions is None:
            seen = {}
            for lib_a in library_artists[:20]:
                for s in discovery.get_similar_artists(lib_a['artistName'], limit=15):
                    name = s['name']
                    if name.lower() in excluded or name in seen:
                        continue
                    info = discovery.get_artist_info(name)
                    listeners = info.get('listeners') if info else None
                    if listeners is not None and listeners < min_listeners:
                        continue
                    seen[name] = {
                        'name':      name,
                        'mbid':      s.get('mbid') or (info or {}).get('mbid', ''),
                        'listeners': listeners,
                        'tags':      (info or {}).get('tags', []),
                        'bio':       (info or {}).get('bio', ''),
                        'image':     (info or {}).get('image', ''),
                        'url':       (info or {}).get('url', ''),
                        'genre':     ', '.join((info or {}).get('tags', [])[:2]),
                        'based_on':  s['based_on'],
                        'match':     s['match'],
                        'source':    'lastfm',
                    }
                    time.sleep(0.1)
            suggestions = sorted(seen.values(), key=lambda x: (x['listeners'] or 0), reverse=True)
            db.set_cached(cache_key, suggestions)

    # ── Trending ─────────────────────────────────────────────────────────────
    elif mode == 'trending':
        if not discovery.listenbrainz:
            return jsonify({'error': 'ListenBrainz is disabled — enable it in Settings.'}), 400

        cache_key   = f'discover_trending:{range_}'
        suggestions = db.get_cached(cache_key, ttl_hours=6)

        if suggestions is None:
            raw = discovery.get_trending_artists(count=200, range_=range_)
            suggestions = []
            for a in raw:
                if a['name'].lower() in excluded:
                    continue
                info = discovery.get_artist_info(a['name'])
                suggestions.append({
                    'name':      a['name'],
                    'mbid':      a.get('mbid') or (info or {}).get('mbid', ''),
                    'listeners': a.get('listeners', 0),
                    'tags':      (info or {}).get('tags', []),
                    'bio':       (info or {}).get('bio', ''),
                    'image':     (info or {}).get('image') or a.get('image', ''),
                    'url':       (info or {}).get('url', ''),
                    'genre':     ', '.join((info or {}).get('tags', [])[:2]),
                    'based_on':  '',
                    'source':    a.get('source', 'listenbrainz'),
                })
                if info:
                    time.sleep(0.1)
            db.set_cached(cache_key, suggestions)

    else:
        return jsonify({'error': f'Unknown mode: {mode}'}), 400

    # Re-filter live (user may have ignored since cache was built)
    suggestions = [s for s in suggestions if s['name'].lower() not in excluded]

    total = len(suggestions)
    start = (page - 1) * per_page
    return jsonify({
        'items': suggestions[start:start + per_page],
        'total': total,
        'page':  page,
        'pages': max(1, (total + per_page - 1) // per_page),
        'mode':  mode,
    })


@app.route('/api/artist/details')
def api_artist_details():
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({'error': 'name required'}), 400
    cache_key = f'artist_detail:{name.lower()}'
    cached = db.get_cached(cache_key, ttl_hours=168)
    if cached:
        return jsonify(cached)
    albums = get_discovery().get_artist_top_albums(name, limit=5)
    result = {'albums': albums}
    db.set_cached(cache_key, result)
    return jsonify(result)


@app.route('/api/artist/lookup')
def api_artist_lookup():
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({'error': 'name required'}), 400
    lidarr = get_lidarr()
    if not lidarr:
        return jsonify({'error': 'Lidarr not configured'}), 400
    try:
        results = lidarr.lookup_artist(name)
        if results:
            return jsonify({'artist': results[0]})
        return jsonify({'error': 'Not found in MusicBrainz'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/artist/add', methods=['POST'])
def api_artist_add():
    data = request.json or {}
    lidarr = get_lidarr()
    if not lidarr:
        return jsonify({'error': 'Lidarr not configured'}), 400
    artist = data.get('artist', {})
    payload = {
        **artist,
        'qualityProfileId':  int(data['qualityProfileId']),
        'metadataProfileId': int(data['metadataProfileId']),
        'rootFolderPath':    data['rootFolderPath'],
        'monitored': True,
        'addOptions': {
            'monitor': data.get('monitor', 'all'),
            'searchForMissingAlbums': data.get('searchForMissingAlbums', True),
        },
    }
    try:
        result = lidarr.add_artist(payload)
        db.mark_added(artist.get('artistName', ''), artist.get('foreignArtistId', ''), result.get('id'))
        return jsonify({'ok': True, 'id': result.get('id')})
    except Exception as e:
        msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                msg = e.response.json()[0].get('errorMessage', msg)
            except Exception:
                pass
        return jsonify({'error': msg}), 500


@app.route('/api/artist/ignore', methods=['POST'])
def api_artist_ignore():
    data = request.json or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'name required'}), 400
    db.ignore_artist(name, data.get('mbid'))
    return jsonify({'ok': True})


@app.route('/api/artist/unignore/<int:artist_id>', methods=['POST'])
def api_artist_unignore(artist_id):
    db.unignore_artist(artist_id)
    return jsonify({'ok': True})


@app.route('/api/lidarr/profiles')
def api_lidarr_profiles():
    lidarr = get_lidarr()
    if not lidarr:
        return jsonify({'error': 'Not configured'}), 400
    cached = db.get_cached('lidarr_profiles', ttl_hours=1)
    if cached:
        return jsonify(cached)
    try:
        result = {
            'quality_profiles':  lidarr.get_quality_profiles(),
            'metadata_profiles': lidarr.get_metadata_profiles(),
            'root_folders':      lidarr.get_root_folders(),
        }
        db.set_cached('lidarr_profiles', result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cache/clear', methods=['POST'])
def api_cache_clear():
    db.clear_cache()
    return jsonify({'ok': True})


# ── Library Health ────────────────────────────────────────────────────────────

@app.route('/library-health')
def library_health():
    if not is_configured():
        return redirect(url_for('settings'))
    return render_template('library_health.html', active='library-health')


@app.route('/api/library/scan')
def api_library_scan():
    from discovery import MusicBrainzSource

    lidarr = get_lidarr()
    if not lidarr:
        return jsonify({'error': 'Lidarr not configured'}), 400

    force = request.args.get('force') == '1'
    if not force:
        cached = db.get_cached('library_health_scan', ttl_hours=24)
        if cached:
            return jsonify(cached)

    # Collect unique artists across all wanted-list pages
    by_artist = {}
    page = 1
    while True:
        try:
            data = lidarr.get_wanted(page=page, page_size=100)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

        for album in data.get('records', []):
            artist = album.get('artist', {})
            aid = artist.get('id')
            if not aid:
                continue
            if aid not in by_artist:
                by_artist[aid] = {
                    'lidarr_id':     aid,
                    'name':          artist.get('artistName', ''),
                    'mbid':          artist.get('foreignArtistId', ''),
                    'missing_count': 0,
                    'missing_titles': [],
                }
            by_artist[aid]['missing_count'] += 1
            title = album.get('title', '')
            if len(by_artist[aid]['missing_titles']) < 6:
                by_artist[aid]['missing_titles'].append(title)

        total = data.get('totalRecords', 0)
        if page * 100 >= total:
            break
        page += 1

    if not by_artist:
        result = {'artists': [], 'scanned_at': datetime.utcnow().isoformat()}
        db.set_cached('library_health_scan', result)
        return jsonify(result)

    mb = MusicBrainzSource()
    artists_out = []

    for a in by_artist.values():
        mbid = a['mbid']
        entry = {**a, 'mb_name': '', 'mb_disambiguation': '', 'status': 'ok', 'issue': ''}

        if not mbid:
            entry.update(status='warning', issue='No MusicBrainz ID linked')
            artists_out.append(entry)
            continue

        mb_info = mb.lookup_by_mbid(mbid)

        if mb_info is None:
            entry.update(status='error', issue='MBID not found in MusicBrainz')
            artists_out.append(entry)
            continue

        mb_name        = mb_info['name']
        disambiguation = mb_info.get('disambiguation', '')
        entry['mb_name']           = mb_name
        entry['mb_disambiguation'] = disambiguation

        ln = _normalize_name(a['name'])
        mn = _normalize_name(mb_name)

        if ln == mn:
            entry['status'] = 'ok'
        elif ln in mn or mn in ln:
            entry['status'] = 'warning'
            entry['issue']  = f'Name differs: MusicBrainz shows "{mb_name}"'
            if disambiguation:
                entry['issue'] += f' ({disambiguation})'
        else:
            entry['status'] = 'error'
            entry['issue']  = f'Name mismatch — MusicBrainz has "{mb_name}"'
            if disambiguation:
                entry['issue'] += f' ({disambiguation})'

        artists_out.append(entry)

    status_order = {'error': 0, 'warning': 1, 'ok': 2}
    artists_out.sort(key=lambda x: (status_order.get(x['status'], 3), x['name'].lower()))

    result = {'artists': artists_out, 'scanned_at': datetime.utcnow().isoformat()}
    db.set_cached('library_health_scan', result)
    return jsonify(result)


@app.route('/api/library/refresh-artist', methods=['POST'])
def api_library_refresh_artist():
    data = request.json or {}
    artist_id = data.get('artist_id')
    if not artist_id:
        return jsonify({'error': 'artist_id required'}), 400
    lidarr = get_lidarr()
    if not lidarr:
        return jsonify({'error': 'Lidarr not configured'}), 400
    try:
        lidarr.refresh_artist(int(artist_id))
        db.clear_cache_key('library_health_scan')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
