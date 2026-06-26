#!/usr/bin/env python3
"""
Deduplication module using SQLite.

Tracks seen offers (url_hash + title_hash composite key), provider usage
(response time monitoring), and search history (cycle-level stats).

Database path: $PICOCLAW_DB_PATH or /data/seen_offers.db
"""

import hashlib
import logging
import os
import sqlite3
from datetime import datetime, timezone, timedelta

log = logging.getLogger("dedup")

DEFAULT_DB_PATH = "/data/seen_offers.db"

_SEEN_OFFERS_SQL = """
CREATE TABLE IF NOT EXISTS seen_offers (
  id TEXT PRIMARY KEY,
  url_hash TEXT NOT NULL,
  title_hash TEXT NOT NULL,
  portal TEXT NOT NULL,
  title TEXT NOT NULL,
  company TEXT,
  score INTEGER,
  notified BOOLEAN DEFAULT 0,
  adapted BOOLEAN DEFAULT 0,
  first_seen DATE NOT NULL,
  last_seen DATE NOT NULL
)
"""

_PROVIDER_USAGE_SQL = """
CREATE TABLE IF NOT EXISTS provider_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  status INTEGER,
  latency_ms INTEGER,
  timestamp DATE NOT NULL
)
"""

_SEARCH_HISTORY_SQL = """
CREATE TABLE IF NOT EXISTS search_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cycle_id TEXT NOT NULL,
  started_at DATE NOT NULL,
  completed_at DATE,
  offers_found INTEGER,
  matches_found INTEGER,
  errors TEXT
)
"""


def _get_db_path() -> str:
    return os.environ.get("PICOCLAW_DB_PATH", DEFAULT_DB_PATH)


def _get_conn() -> sqlite3.Connection:
    path = _get_db_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_tables(conn: sqlite3.Connection) -> None:
    for ddl in (_SEEN_OFFERS_SQL, _PROVIDER_USAGE_SQL, _SEARCH_HISTORY_SQL):
        conn.execute(ddl)
    conn.commit()


_now = lambda: datetime.now(timezone.utc)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def is_seen(url: str, title: str) -> bool:
    conn = _get_conn()
    try:
        _ensure_tables(conn)
        url_hash = _hash(url)
        title_hash = _hash(title)
        cursor = conn.execute(
            "SELECT 1 FROM seen_offers WHERE url_hash = ? AND title_hash = ? LIMIT 1",
            (url_hash, title_hash),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def mark_seen(
    url: str,
    title: str,
    portal: str,
    title_text: str,
    company: str = "",
    score: int = 0,
) -> None:
    conn = _get_conn()
    try:
        _ensure_tables(conn)
        url_hash = _hash(url)
        title_hash = _hash(title)
        today = _now().date().isoformat()
        offer_id = f"{url_hash}|{title_hash}"
        conn.execute(
            """INSERT INTO seen_offers
               (id, url_hash, title_hash, portal, title, company, score,
                notified, adapted, first_seen, last_seen)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 last_seen = ?,
                 score = ?""",
            (
                offer_id,
                url_hash,
                title_hash,
                portal,
                title_text,
                company,
                score,
                today,
                today,
                today,
                score,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def mark_notified(offer_id: str) -> None:
    conn = _get_conn()
    try:
        _ensure_tables(conn)
        conn.execute("UPDATE seen_offers SET notified = 1 WHERE id = ?", (offer_id,))
        conn.commit()
    finally:
        conn.close()


def mark_adapted(offer_id: str) -> None:
    conn = _get_conn()
    try:
        _ensure_tables(conn)
        conn.execute("UPDATE seen_offers SET adapted = 1 WHERE id = ?", (offer_id,))
        conn.commit()
    finally:
        conn.close()


def get_recent(days: int = 7) -> list:
    conn = _get_conn()
    try:
        _ensure_tables(conn)
        since = (_now() - timedelta(days=days)).date().isoformat()
        cursor = conn.execute(
            "SELECT * FROM seen_offers WHERE last_seen >= ? ORDER BY last_seen DESC",
            (since,),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def log_provider_usage(
    provider: str, endpoint: str, status: int, latency_ms: int
) -> None:
    conn = _get_conn()
    try:
        _ensure_tables(conn)
        today = _now().date().isoformat()
        conn.execute(
            "INSERT INTO provider_usage (provider, endpoint, status, latency_ms, timestamp) VALUES (?, ?, ?, ?, ?)",
            (provider, endpoint, status, latency_ms, today),
        )
        conn.commit()
    finally:
        conn.close()


def start_cycle(cycle_id: str) -> None:
    conn = _get_conn()
    try:
        _ensure_tables(conn)
        today = _now().date().isoformat()
        conn.execute(
            "INSERT INTO search_history (cycle_id, started_at) VALUES (?, ?)",
            (cycle_id, today),
        )
        conn.commit()
    finally:
        conn.close()


def complete_cycle(
    cycle_id: str,
    offers_found: int,
    matches_found: int,
    errors: str = "",
) -> None:
    conn = _get_conn()
    try:
        _ensure_tables(conn)
        today = _now().date().isoformat()
        conn.execute(
            "UPDATE search_history SET completed_at = ?, offers_found = ?, matches_found = ?, errors = ? WHERE cycle_id = ?",
            (today, offers_found, matches_found, errors, cycle_id),
        )
        conn.commit()
    finally:
        conn.close()


def cleanup() -> int:
    total = 0
    conn = _get_conn()
    try:
        _ensure_tables(conn)
        cutoff_seen = (_now() - timedelta(days=30)).date().isoformat()
        cursor = conn.execute(
            "DELETE FROM seen_offers WHERE last_seen < ?", (cutoff_seen,)
        )
        total += cursor.rowcount

        cutoff_provider = (_now() - timedelta(days=7)).date().isoformat()
        cursor = conn.execute(
            "DELETE FROM provider_usage WHERE timestamp < ?", (cutoff_provider,)
        )
        total += cursor.rowcount

        cutoff_history = (_now() - timedelta(days=90)).date().isoformat()
        cursor = conn.execute(
            "DELETE FROM search_history WHERE started_at < ?", (cutoff_history,)
        )
        total += cursor.rowcount

        conn.commit()
        return total
    finally:
        conn.close()
