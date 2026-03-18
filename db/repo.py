"""CRUD helpers for the LinkedinTouch database."""
import json
import sqlite3
from datetime import date
from typing import Optional

from db.schema import init_db
import config


def _conn() -> sqlite3.Connection:
    return init_db(config.DB_FILE)


# ── Prospects ────────────────────────────────────────────────────────────────

def upsert_prospect(
    profile_url: str,
    name: str = "",
    headline: str = "",
    company: str = "",
    location: str = "",
    about: str = "",
    experiences: list | None = None,
) -> int:
    """Insert or update a prospect row. Returns the prospect id."""
    conn = _conn()
    experiences_json = json.dumps(experiences or [])
    cur = conn.execute(
        """
        INSERT INTO prospects (profile_url, name, headline, company, location, about, experiences)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(profile_url) DO UPDATE SET
            name        = excluded.name,
            headline    = excluded.headline,
            company     = excluded.company,
            location    = excluded.location,
            about       = excluded.about,
            experiences = excluded.experiences,
            scraped_at  = datetime('now')
        """,
        (profile_url, name, headline, company, location, about, experiences_json),
    )
    conn.commit()
    # Fetch id (works for both insert and update)
    row = conn.execute(
        "SELECT id FROM prospects WHERE profile_url = ?", (profile_url,)
    ).fetchone()
    conn.close()
    return row["id"]


def get_existing_profile_urls() -> set[str]:
    """Return the set of all profile URLs already in the database."""
    conn = _conn()
    rows = conn.execute("SELECT profile_url FROM prospects").fetchall()
    conn.close()
    return {row["profile_url"] for row in rows}


def get_pending_prospects() -> list[sqlite3.Row]:
    """Return all prospects with status='new' that have no pending/sent message."""
    conn = _conn()
    rows = conn.execute(
        """
        SELECT p.*
        FROM prospects p
        LEFT JOIN messages m ON m.prospect_id = p.id AND m.status IN ('pending','sent')
        WHERE p.status = 'new' AND m.id IS NULL
        ORDER BY p.scraped_at
        """
    ).fetchall()
    conn.close()
    return rows


def set_prospect_status(prospect_id: int, status: str) -> None:
    conn = _conn()
    conn.execute(
        "UPDATE prospects SET status = ? WHERE id = ?", (status, prospect_id)
    )
    conn.commit()
    conn.close()


# ── Messages ─────────────────────────────────────────────────────────────────

def save_message(prospect_id: int, message_text: str) -> int:
    conn = _conn()
    cur = conn.execute(
        "INSERT INTO messages (prospect_id, message_text) VALUES (?, ?)",
        (prospect_id, message_text),
    )
    conn.commit()
    msg_id = cur.lastrowid
    conn.close()
    return msg_id


def get_pending_messages() -> list[sqlite3.Row]:
    conn = _conn()
    rows = conn.execute(
        """
        SELECT m.*, p.profile_url, p.name
        FROM messages m
        JOIN prospects p ON p.id = m.prospect_id
        WHERE m.status = 'pending'
        ORDER BY m.generated_at
        """
    ).fetchall()
    conn.close()
    return rows


def mark_sent(message_id: int) -> None:
    conn = _conn()
    conn.execute(
        "UPDATE messages SET status='sent', sent_at=datetime('now') WHERE id=?",
        (message_id,),
    )
    conn.commit()
    conn.close()


def mark_message_failed(message_id: int) -> None:
    conn = _conn()
    conn.execute(
        "UPDATE messages SET status='failed' WHERE id=?", (message_id,)
    )
    conn.commit()
    conn.close()


# ── Daily counts ─────────────────────────────────────────────────────────────

def _today() -> str:
    return date.today().isoformat()


def _ensure_today(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO daily_counts (date) VALUES (?)", (_today(),)
    )


def get_daily_counts() -> dict:
    conn = _conn()
    _ensure_today(conn)
    conn.commit()
    row = conn.execute(
        "SELECT scraped, messaged FROM daily_counts WHERE date = ?", (_today(),)
    ).fetchone()
    conn.close()
    return {"scraped": row["scraped"], "messaged": row["messaged"]}


def increment_scraped() -> None:
    conn = _conn()
    _ensure_today(conn)
    conn.execute(
        "UPDATE daily_counts SET scraped = scraped + 1 WHERE date = ?", (_today(),)
    )
    conn.commit()
    conn.close()


def increment_messaged() -> None:
    conn = _conn()
    _ensure_today(conn)
    conn.execute(
        "UPDATE daily_counts SET messaged = messaged + 1 WHERE date = ?", (_today(),)
    )
    conn.commit()
    conn.close()


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_stats() -> dict:
    conn = _conn()
    stats = {}
    for status in ("new", "messaged", "skipped", "failed"):
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM prospects WHERE status = ?", (status,)
        ).fetchone()
        stats[status] = row["cnt"]

    row = conn.execute("SELECT COUNT(*) AS cnt FROM messages WHERE status='sent'").fetchone()
    stats["messages_sent"] = row["cnt"]

    row = conn.execute("SELECT COUNT(*) AS cnt FROM messages WHERE status='failed'").fetchone()
    stats["messages_failed"] = row["cnt"]

    conn.close()
    return stats
