"""Create SQLite tables if they don't exist."""
import sqlite3
import config


def init_db(db_path: str = config.DB_FILE) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filters_json TEXT NOT NULL,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS prospects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_url TEXT UNIQUE NOT NULL,
            name        TEXT,
            headline    TEXT,
            company     TEXT,
            location    TEXT,
            about       TEXT,
            experiences TEXT,   -- JSON list of top-3 experiences
            scraped_at  TEXT NOT NULL DEFAULT (datetime('now')),
            status      TEXT NOT NULL DEFAULT 'new'
                            CHECK(status IN ('new','messaged','skipped','failed'))
        );

        CREATE TABLE IF NOT EXISTS messages (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            prospect_id  INTEGER NOT NULL REFERENCES prospects(id),
            message_text TEXT NOT NULL,
            generated_at TEXT NOT NULL DEFAULT (datetime('now')),
            sent_at      TEXT,
            status       TEXT NOT NULL DEFAULT 'pending'
                             CHECK(status IN ('pending','sent','failed'))
        );

        CREATE TABLE IF NOT EXISTS daily_counts (
            date         TEXT PRIMARY KEY,
            scraped      INTEGER NOT NULL DEFAULT 0,
            messaged     INTEGER NOT NULL DEFAULT 0
        );
    """)
    conn.commit()
    return conn
