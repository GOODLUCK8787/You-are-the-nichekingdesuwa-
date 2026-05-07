import sqlite3
import os
from contextlib import contextmanager

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "db")
DB_PATH = os.path.abspath(os.path.join(DB_DIR, "yinyue.db"))
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def _load_schema() -> str:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return f.read()


def init_db() -> str:
    """Create database and tables. Returns path to the database file."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(_load_schema())
    conn.commit()
    conn.close()
    return DB_PATH


@contextmanager
def get_db(readonly: bool = False):
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if readonly:
            conn.execute("PRAGMA query_only = ON")
        yield conn
    finally:
        conn.close()


# --- CRUD helpers ---

def save_playlist(playlist: dict) -> int:
    """Insert or update a playlist. Returns the internal DB id."""
    with get_db() as db:
        existing = db.execute(
            "SELECT id FROM playlists WHERE netease_id = ?", (playlist["netease_id"],)
        ).fetchone()
        if existing:
            db.execute("""
                UPDATE playlists SET name=?, description=?, owner_name=?, owner_id=?,
                song_count=?, play_count=?, share_count=?, comment_count=?, tags=?,
                create_time=?, update_time=?, scraped_at=CURRENT_TIMESTAMP, url=?
                WHERE netease_id=?
            """, (
                playlist["name"], playlist.get("description"), playlist["owner_name"],
                playlist.get("owner_id"), playlist["song_count"], playlist.get("play_count", 0),
                playlist.get("share_count", 0), playlist.get("comment_count", 0),
                playlist.get("tags"), playlist.get("create_time"), playlist.get("update_time"),
                playlist["url"], playlist["netease_id"]
            ))
            return existing["id"]
        else:
            cursor = db.execute("""
                INSERT INTO playlists (netease_id, name, description, owner_name, owner_id,
                song_count, play_count, share_count, comment_count, tags, create_time,
                update_time, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                playlist["netease_id"], playlist["name"], playlist.get("description"),
                playlist["owner_name"], playlist.get("owner_id"), playlist["song_count"],
                playlist.get("play_count", 0), playlist.get("share_count", 0),
                playlist.get("comment_count", 0), playlist.get("tags"),
                playlist.get("create_time"), playlist.get("update_time"), playlist["url"]
            ))
            return cursor.lastrowid


def save_song(playlist_db_id: int, song: dict):
    """Insert a song and link it to a playlist."""
    import json
    with get_db() as db:
        db.execute("""
            INSERT OR IGNORE INTO songs (netease_id, name, artists_json, album_name,
            album_id, duration_ms, play_count, popularity, genre_tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            song["netease_id"], song["name"],
            json.dumps(song.get("artists", []), ensure_ascii=False),
            song.get("album_name"), song.get("album_id"), song.get("duration_ms", 0),
            song.get("play_count", 0), song.get("popularity", 0),
            json.dumps(song.get("genre_tags", []), ensure_ascii=False)
        ))


def playlist_exists(netease_id: int) -> bool:
    """Check if a playlist is already cached."""
    with get_db(readonly=True) as db:
        row = db.execute(
            "SELECT 1 FROM playlists WHERE netease_id = ?", (netease_id,)
        ).fetchone()
        return row is not None


def get_cached_playlist(netease_id: int) -> dict | None:
    """Load a cached playlist from DB."""
    with get_db(readonly=True) as db:
        row = db.execute(
            "SELECT * FROM playlists WHERE netease_id = ?", (netease_id,)
        ).fetchone()
        if row is None:
            return None
        return dict(row)
