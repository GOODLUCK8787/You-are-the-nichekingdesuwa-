CREATE TABLE IF NOT EXISTS playlists (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    netease_id      BIGINT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    description     TEXT,
    owner_name      TEXT NOT NULL,
    owner_id        BIGINT,
    song_count      INTEGER NOT NULL,
    play_count      BIGINT,
    share_count     INTEGER,
    comment_count   INTEGER,
    tags            TEXT,
    create_time     BIGINT,
    update_time     BIGINT,
    scraped_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    url             TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS songs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    netease_id      BIGINT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    artists_json    TEXT NOT NULL,
    album_name      TEXT,
    album_id        BIGINT,
    duration_ms     INTEGER,
    play_count      BIGINT,
    popularity      REAL,
    genre_tags      TEXT,
    scraped_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS niche_scores (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id             INTEGER NOT NULL UNIQUE REFERENCES songs(id),
    overall_score       REAL NOT NULL,
    play_count_score    REAL NOT NULL,
    penetration_score   REAL NOT NULL,
    artist_indie_score  REAL NOT NULL,
    genre_rarity_score  REAL NOT NULL,
    percentile_rank     REAL,
    computed_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analysis_reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id     INTEGER NOT NULL REFERENCES playlists(id),
    roast_text      TEXT,
    roast_score     REAL,
    summary_json    TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_songs_popularity ON songs(popularity);
CREATE INDEX IF NOT EXISTS idx_niche_scores_overall ON niche_scores(overall_score DESC);
