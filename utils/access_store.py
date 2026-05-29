"""SQLite helpers for token ownership, ban state, and request logs."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from config import DB_PATH, LOGS_DIR


TOKEN_OWNERS_TABLE = "token_owners"
TOKEN_INDEX_TABLE = "token_index"


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def ensure_storage() -> None:
    """Create the runtime tables used by the main API."""
    LOGS_DIR.mkdir(exist_ok=True, parents=True)

    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TOKEN_OWNERS_TABLE} (
                owner_id TEXT PRIMARY KEY,
                tokens_json TEXT NOT NULL DEFAULT '[]',
                is_banned INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            )
            """
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TOKEN_INDEX_TABLE} (
                access_token TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                last_seen_at INTEGER NOT NULL
            )
            """
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{TOKEN_INDEX_TABLE}_owner_id "
            f"ON {TOKEN_INDEX_TABLE}(owner_id)"
        )


def _load_tokens(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if item]


def _dump_tokens(tokens: Iterable[str]) -> str:
    unique_tokens = []
    seen = set()
    for token in tokens:
        token = str(token)
        if token and token not in seen:
            unique_tokens.append(token)
            seen.add(token)
    return json.dumps(unique_tokens, ensure_ascii=False)


def extract_owner_id(context_data: Dict[str, Any]) -> Optional[str]:
    """Extract a stable owner identifier from the Dnevnik context payload."""
    candidates = [
        context_data.get("userId"),
        context_data.get("personId"),
        context_data.get("id"),
    ]

    for candidate in candidates:
        if candidate is None:
            continue
        candidate_str = str(candidate).strip()
        if candidate_str:
            return candidate_str
    return None


def get_owner_id_by_token(access_token: str) -> Optional[str]:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT owner_id FROM {TOKEN_INDEX_TABLE} WHERE access_token = ?",
            (access_token,),
        )
        row = cur.fetchone()
        return row[0] if row else None


def is_owner_banned(owner_id: str) -> bool:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT is_banned FROM {TOKEN_OWNERS_TABLE} WHERE owner_id = ?",
            (owner_id,),
        )
        row = cur.fetchone()
        return bool(row and row[0])


def register_token_owner(access_token: str, owner_id: str) -> None:
    """Store the owner row and token index on first token discovery."""
    now = int(time.time())

    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT tokens_json, created_at FROM {TOKEN_OWNERS_TABLE} WHERE owner_id = ?",
            (owner_id,),
        )
        row = cur.fetchone()

        if row:
            tokens = _load_tokens(row[0])
            if access_token not in tokens:
                tokens.append(access_token)
            cur.execute(
                f"""
                UPDATE {TOKEN_OWNERS_TABLE}
                SET tokens_json = ?
                WHERE owner_id = ?
                """,
                (_dump_tokens(tokens), owner_id),
            )
        else:
            cur.execute(
                f"""
                INSERT INTO {TOKEN_OWNERS_TABLE} (owner_id, tokens_json, is_banned, created_at)
                VALUES (?, ?, 0, ?)
                """,
                (owner_id, _dump_tokens([access_token]), now),
            )

        cur.execute(
            f"""
            INSERT INTO {TOKEN_INDEX_TABLE} (access_token, owner_id, created_at, last_seen_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(access_token) DO UPDATE SET
                owner_id = excluded.owner_id,
                last_seen_at = excluded.last_seen_at
            """,
            (access_token, owner_id, now, now),
        )


def touch_token(access_token: str, owner_id: str) -> None:
    """Refresh token usage without asking the context again."""
    now = int(time.time())
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            INSERT INTO {TOKEN_INDEX_TABLE} (access_token, owner_id, created_at, last_seen_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(access_token) DO UPDATE SET
                owner_id = excluded.owner_id,
                last_seen_at = excluded.last_seen_at
            """,
            (access_token, owner_id, now, now),
        )


def append_request_log(owner_id: str, record: Dict[str, Any]) -> Path:
    """Append a JSON log line into the owner-specific file."""
    LOGS_DIR.mkdir(exist_ok=True, parents=True)
    log_path = Path(LOGS_DIR) / f"{owner_id}.jsonl"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return log_path
