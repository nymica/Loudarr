import requests
import time

LASTFM_BASE      = 'https://ws.audioscrobbler.com/2.0'
MUSICBRAINZ_BASE = 'https://musicbrainz.org/ws/2'
DEEZER_BASE      = 'https://api.deezer.com'
LISTENBRAINZ_BASE = 'https://api.listenbrainz.org/1'

_UA = 'Loudarr/1.0 (https://github.com/loudarr)'


# ── Last.fm ────────────────────────────────────────────────────────────────

class LastFMSource:
    def __init__(self, api_key):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers['User-Agent'] = _UA

    def _call(self, method, params, retries=2):
        p = {'method': method, 'api_key': self.api_key, 'format': 'json', **params}
        for attempt in range(retries + 1):
            try:
                r = self.session.get(LASTFM_BASE, params=p, timeout=10)
                r.raise_for_status()
                data = r.json()
                return None if 'error' in data else data
            except Exception:
                if attempt < retries:
                    time.sleep(0.5 * (attempt + 1))
        return None

    def get_artists_by_tag(self, tag, limit=100):
        data = self._call('tag.getTopArtists', {'tag': tag, 'limit': limit})
        if not data:
            return []
        return [
            {'name': a['name'], 'mbid': a.get('mbid', ''), 'listeners': None,
             'url': a.get('url', ''), 'source': 'lastfm'}
            for a in data.get('topartists', {}).get('artist', [])
        ]

    def get_similar_artists(self, artist_name, limit=15):
        data = self._call('artist.getSimilar', {'artist': artist_name, 'limit': limit})
        if not data:
            return []
        return [
            {'name': a['name'], 'mbid': a.get('mbid', ''),
             'match': float(a.get('match', 0)), 'url': a.get('url', ''),
             'based_on': artist_name, 'source': 'lastfm'}
            for a in data.get('similarartists', {}).get('artist', [])
        ]

    def get_artist_info(self, artist_name):
        data = self._call('artist.getInfo', {'artist': artist_name, 'autocorrect': 1})
        if not data or 'artist' not in data:
            return {}
        a = data['artist']
        stats = a.get('stats', {})
        bio = a.get('bio', {}).get('summary', '')
        bio = bio.split('<a href')[0].strip()
        images = a.get('image', [])
        image = next((i['#text'] for i in reversed(images) if i.get('#text')), '')
        return {
            'name': a.get('name', artist_name),
            'mbid': a.get('mbid', ''),
            'listeners': int(stats.get('listeners', 0)),
            'playcount': int(stats.get('playcount', 0)),
            'bio': bio,
            'tags': [t['name'] for t in a.get('tags', {}).get('tag', [])[:5]],
            'url': a.get('url', ''),
            'image': image,
            'source': 'lastfm',
        }

    def get_artist_top_albums(self, artist_name, limit=5):
        data = self._call('artist.getTopAlbums', {'artist': artist_name, 'limit': limit})
        if not data:
            return []
        return [
            {'name': a['name'],
             'image': next((i['#text'] for i in reversed(a.get('image', [])) if i.get('#text')), '')}
            for a in data.get('topalbums', {}).get('album', [])
        ]


# ── MusicBrainz ────────────────────────────────────────────────────────────

class MusicBrainzSource:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = _UA
        self._last = 0.0

    def _throttle(self):
        wait = 1.1 - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()

    def _get(self, endpoint, params):
        self._throttle()
        try:
            r = self.session.get(f'{MUSICBRAINZ_BASE}/{endpoint}',
                                 params={**params, 'fmt': 'json'}, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception:
            return {}

    def get_artists_by_tag(self, tag, limit=50):
        data = self._get('artist', {'query': f'tag:{tag}', 'limit': min(limit, 100)})
        out = []
        tag_words = set(tag.lower().replace('-', ' ').split())
        for a in data.get('artists', []):
            artist_tags = [t['name'].lower() for t in a.get('tags', [])]
            if artist_tags:
                # Only include artists whose tags have word overlap with the searched tag.
                # Without this, popular artists with many diverse tags appear in every genre.
                artist_tag_words = set()
                for at in artist_tags:
                    artist_tag_words.update(at.replace('-', ' ').split())
                if not (tag_words & artist_tag_words):
                    continue
            out.append({
                'name': a['name'],
                'mbid': a.get('id', ''),
                'listeners': None,
                'tags': [t['name'] for t in a.get('tags', [])[:5]],
                'source': 'musicbrainz',
            })
        return out

    def lookup_by_mbid(self, mbid):
        """Return canonical name and disambiguation for a known MBID, or None if not found."""
        if not mbid:
            return None
        self._throttle()
        try:
            r = self.session.get(
                f'{MUSICBRAINZ_BASE}/artist/{mbid}',
                params={'fmt': 'json'},
                timeout=15,
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            data = r.json()
            return {
                'name':           data.get('name', ''),
                'disambiguation': data.get('disambiguation', ''),
                'type':           data.get('type', ''),
            }
        except Exception:
            return None

    def get_artist_info(self, artist_name):
        data = self._get('artist', {'query': f'artist:"{artist_name}"', 'limit': 1})
        artists = data.get('artists', [])
        if not artists:
            return {}
        a = artists[0]
        if a['name'].lower() != artist_name.lower():
            return {}
        return {
            'name': a['name'],
            'mbid': a.get('id', ''),
            'listeners': None,
            'tags': [t['name'] for t in a.get('tags', [])[:5]],
            'bio': '',
            'image': '',
            'url': f"https://musicbrainz.org/artist/{a.get('id', '')}",
            'source': 'musicbrainz',
        }


# ── Deezer ─────────────────────────────────────────────────────────────────

# Deezer genre IDs for tags that can't be found via name matching
_DEEZER_OVERRIDES = {
    'hip-hop': 116, 'hip hop': 116, 'rap': 116,
    'r&b': 165, 'rnb': 165,
    'electronic': 113, 'electronica': 113,
}


class DeezerSource:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = _UA
        self._genres = None

    def _get_genres(self):
        if self._genres is None:
            try:
                r = self.session.get(f'{DEEZER_BASE}/genre', timeout=10)
                r.raise_for_status()
                self._genres = r.json().get('data', [])
            except Exception:
                self._genres = []
        return self._genres

    def _find_genre_id(self, tag):
        tag_l = tag.lower().strip()
        # Curated overrides for tags whose names don't match Deezer genre names
        if tag_l in _DEEZER_OVERRIDES:
            return _DEEZER_OVERRIDES[tag_l]
        # Exact name match
        for g in self._get_genres():
            if g['name'].lower() == tag_l:
                return g['id']
        # Word-set match: every word in the Deezer genre name must appear in the tag.
        # e.g. tag="classic rock" matches Deezer "Rock" ({"rock"} ≤ {"classic","rock"}).
        # Skips genre 0 ("All") — returning the global chart for any unmatched tag is wrong.
        tag_words = set(tag_l.replace('-', ' ').split())
        for g in self._get_genres():
            if g['id'] == 0:
                continue
            gn_words = set(g['name'].lower().replace('-', ' ').split())
            if gn_words and gn_words <= tag_words:
                return g['id']
        return None

    def get_artists_by_tag(self, tag, limit=50):
        genre_id = self._find_genre_id(tag)
        if not genre_id:
            return []
        try:
            r = self.session.get(f'{DEEZER_BASE}/genre/{genre_id}/artists', timeout=10)
            r.raise_for_status()
            out = []
            for a in r.json().get('data', [])[:limit]:
                out.append({
                    'name': a['name'],
                    'mbid': '',
                    'listeners': a.get('nb_fan') or 0,
                    'tags': [],
                    'image': a.get('picture_medium', ''),
                    'url': a.get('link', ''),
                    'source': 'deezer',
                })
            return out
        except Exception:
            return []

    def search_artist(self, artist_name):
        try:
            r = self.session.get(f'{DEEZER_BASE}/search/artist',
                                 params={'q': artist_name, 'limit': 1}, timeout=8)
            r.raise_for_status()
            data = r.json().get('data', [])
            if data and data[0]['name'].lower() == artist_name.lower():
                a = data[0]
                return {
                    'name': a['name'],
                    'mbid': '',
                    'listeners': a.get('nb_fan') or 0,
                    'tags': [],
                    'image': a.get('picture_medium', ''),
                    'url': a.get('link', ''),
                    'source': 'deezer',
                }
        except Exception:
            pass
        return {}


# ── ListenBrainz ───────────────────────────────────────────────────────────

class ListenBrainzSource:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = _UA

    def get_trending_artists(self, count=150, range_='month'):
        try:
            r = self.session.get(
                f'{LISTENBRAINZ_BASE}/stats/sitewide/artists',
                params={'count': count, 'range': range_},
                timeout=15,
            )
            r.raise_for_status()
            artists = r.json().get('payload', {}).get('artists', [])
            return [
                {
                    'name': a['artist_name'],
                    'mbid': (a.get('artist_mbids') or [''])[0],
                    'listeners': a.get('listen_count', 0),
                    'tags': [],
                    'source': 'listenbrainz',
                }
                for a in artists
            ]
        except Exception:
            return []


# ── Engine ─────────────────────────────────────────────────────────────────

class DiscoveryEngine:
    def __init__(self, lastfm_api_key=None, enabled_sources=None):
        enabled = set(enabled_sources or ['lastfm', 'musicbrainz', 'deezer', 'listenbrainz'])

        self.lastfm      = LastFMSource(lastfm_api_key) if lastfm_api_key and 'lastfm' in enabled else None
        self.musicbrainz = MusicBrainzSource()          if 'musicbrainz' in enabled else None
        self.deezer      = DeezerSource()               if 'deezer'      in enabled else None
        self.listenbrainz = ListenBrainzSource()        if 'listenbrainz' in enabled else None

    def any_genre_source(self):
        return any([self.lastfm, self.musicbrainz, self.deezer])

    def get_artists_by_tag(self, tag, limit=100):
        merged = {}  # lower(name) -> artist dict

        if self.lastfm:
            for a in self.lastfm.get_artists_by_tag(tag, limit):
                merged[a['name'].lower()] = a
            time.sleep(0.1)

        if self.deezer:
            for a in self.deezer.get_artists_by_tag(tag, limit):
                key = a['name'].lower()
                if key not in merged:
                    merged[key] = a
                elif not merged[key].get('image') and a.get('image'):
                    merged[key]['image'] = a['image']

        if self.musicbrainz:
            for a in self.musicbrainz.get_artists_by_tag(tag, min(limit, 50)):
                key = a['name'].lower()
                if key not in merged:
                    merged[key] = a
                elif not merged[key].get('mbid') and a.get('mbid'):
                    merged[key]['mbid'] = a['mbid']

        return list(merged.values())

    def get_similar_artists(self, artist_name, limit=15):
        if not self.lastfm:
            return []
        return self.lastfm.get_similar_artists(artist_name, limit)

    def get_trending_artists(self, count=150, range_='month'):
        if not self.listenbrainz:
            return []
        return self.listenbrainz.get_trending_artists(count, range_)

    def get_artist_info(self, artist_name):
        """Enrich an artist with bio/listeners/image, trying sources in order."""
        if self.lastfm:
            info = self.lastfm.get_artist_info(artist_name)
            if info:
                return info
        if self.deezer:
            info = self.deezer.search_artist(artist_name)
            if info:
                return info
        if self.musicbrainz:
            info = self.musicbrainz.get_artist_info(artist_name)
            if info:
                return info
        return {}

    def get_artist_top_albums(self, artist_name, limit=5):
        if self.lastfm:
            return self.lastfm.get_artist_top_albums(artist_name, limit)
        return []
