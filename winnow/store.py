"""sqlite3-backed observability store: one row per proxied /v1/messages
request, with before/after token estimates and a breakdown of what happened
to the older content (kept verbatim / truncated / dropped-as-stub).
"""
import json
import os
import sqlite3
import time

from winnow import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    tokens_before INTEGER NOT NULL,
    tokens_after INTEGER NOT NULL,
    kept INTEGER NOT NULL DEFAULT 0,
    truncated INTEGER NOT NULL DEFAULT 0,
    dropped INTEGER NOT NULL DEFAULT 0,
    mode TEXT NOT NULL,
    detail TEXT
);
"""


def _connect(db_path: str = None) -> sqlite3.Connection:
    path = db_path or config.db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(_SCHEMA)
    return conn


def log_request(tokens_before: int, tokens_after: int, kept: int = 0, truncated: int = 0,
                 dropped: int = 0, mode: str = "thorough", detail: dict = None, db_path: str = None) -> None:
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT INTO requests (ts, tokens_before, tokens_after, kept, truncated, dropped, mode, detail) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (time.time(), tokens_before, tokens_after, kept, truncated, dropped, mode,
             json.dumps(detail) if detail is not None else None),
        )
        conn.commit()
    finally:
        conn.close()


def query_recent(limit: int = 20, db_path: str = None) -> list:
    conn = _connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM requests ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def aggregate_savings(db_path: str = None) -> dict:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(tokens_before),0) AS before_sum, "
            "COALESCE(SUM(tokens_after),0) AS after_sum FROM requests"
        ).fetchone()
        n, before_sum, after_sum = row
        saved = before_sum - after_sum
        pct = (saved / before_sum * 100.0) if before_sum else 0.0
        return {
            "requests": n,
            "tokens_before_total": before_sum,
            "tokens_after_total": after_sum,
            "tokens_saved_total": saved,
            "pct_saved": pct,
        }
    finally:
        conn.close()
