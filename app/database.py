import sqlite3
import json
import os
from datetime import datetime, timedelta

DATABASE = os.getenv('DATABASE_PATH', '/data/loudarr.db')


def get_db():
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def init_db():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    with get_db() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS ignored_artists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_name TEXT NOT NULL,
                mbid TEXT,
                ignored_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(artist_name COLLATE NOCASE)
            );
            CREATE TABLE IF NOT EXISTS added_artists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_name TEXT NOT NULL,
                mbid TEXT,
                lidarr_id INTEGER,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(artist_name COLLATE NOCASE)
            );
            CREATE TABLE IF NOT EXISTS discovery_cache (
                cache_key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                cached_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        ''')


def get_config():
    with get_db() as conn:
        rows = conn.execute('SELECT key, value FROM config').fetchall()
        return {row['key']: row['value'] for row in rows}


def set_config(key, value):
    with get_db() as conn:
        conn.execute(
            'INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)',
            (key, str(value) if value is not None else '')
        )


def is_ignored(artist_name):
    with get_db() as conn:
        row = conn.execute(
            'SELECT id FROM ignored_artists WHERE artist_name = ? COLLATE NOCASE',
            (artist_name,)
        ).fetchone()
        return row is not None


def ignore_artist(artist_name, mbid=None):
    with get_db() as conn:
        conn.execute(
            'INSERT OR IGNORE INTO ignored_artists (artist_name, mbid) VALUES (?, ?)',
            (artist_name, mbid)
        )


def unignore_artist(artist_id):
    with get_db() as conn:
        conn.execute('DELETE FROM ignored_artists WHERE id = ?', (artist_id,))


def get_ignored_artists():
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            'SELECT * FROM ignored_artists ORDER BY ignored_at DESC'
        ).fetchall()]


def is_added(artist_name):
    with get_db() as conn:
        row = conn.execute(
            'SELECT id FROM added_artists WHERE artist_name = ? COLLATE NOCASE',
            (artist_name,)
        ).fetchone()
        return row is not None


def mark_added(artist_name, mbid=None, lidarr_id=None):
    with get_db() as conn:
        conn.execute(
            'INSERT OR REPLACE INTO added_artists (artist_name, mbid, lidarr_id) VALUES (?, ?, ?)',
            (artist_name, mbid, lidarr_id)
        )


def get_added_artists():
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            'SELECT * FROM added_artists ORDER BY added_at DESC'
        ).fetchall()]


def get_cached(cache_key, ttl_hours=24):
    with get_db() as conn:
        row = conn.execute(
            'SELECT data, cached_at FROM discovery_cache WHERE cache_key = ?',
            (cache_key,)
        ).fetchone()
        if row:
            cached_at = datetime.fromisoformat(row['cached_at'])
            if datetime.utcnow() - cached_at < timedelta(hours=ttl_hours):
                return json.loads(row['data'])
    return None


def set_cached(cache_key, data):
    with get_db() as conn:
        conn.execute(
            'INSERT OR REPLACE INTO discovery_cache (cache_key, data, cached_at) VALUES (?, ?, ?)',
            (cache_key, json.dumps(data), datetime.utcnow().isoformat())
        )


def clear_cache():
    with get_db() as conn:
        conn.execute('DELETE FROM discovery_cache')


def clear_cache_key(cache_key):
    with get_db() as conn:
        conn.execute('DELETE FROM discovery_cache WHERE cache_key = ?', (cache_key,))
