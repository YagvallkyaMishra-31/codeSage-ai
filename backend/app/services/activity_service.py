"""
Activity service: stores and retrieves debug activity records.
Uses a direct sqlite3 connection for writes to avoid aiosqlite lock contention.
"""
import asyncio
import logging
import sqlite3
from pathlib import Path
from app.database.db import get_db
from app.config import DB_PATH

logger = logging.getLogger(__name__)


def _save_activity_sync(
    error_text: str,
    root_cause: str = "",
    explanation: str = "",
    suggested_fix: str = "",
    code_patch: str = "",
    severity: str = "medium",
    category: str = "ERROR",
    file_path: str = "",
    repo_id: int | None = None,
) -> int:
    """
    Synchronous activity save using a direct sqlite3 connection.
    This bypasses the async connection pool to avoid lock contention.
    """
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    try:
        cursor = conn.execute(
            """INSERT INTO debug_activity
               (repo_id, error_text, root_cause, explanation, suggested_fix,
                code_patch, severity, category, file_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (repo_id, error_text, root_cause, explanation, suggested_fix,
             code_patch, severity, category, file_path)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


async def save_activity(
    error_text: str,
    root_cause: str = "",
    explanation: str = "",
    suggested_fix: str = "",
    code_patch: str = "",
    severity: str = "medium",
    category: str = "ERROR",
    file_path: str = "",
    repo_id: int | None = None,
) -> int:
    """
    Save a debug activity record to the database.
    Uses sync sqlite3 in a thread pool to avoid aiosqlite lock contention.
    """
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            _save_activity_sync,
            error_text, root_cause, explanation, suggested_fix,
            code_patch, severity, category, file_path, repo_id,
        )
        logger.info("Activity saved successfully (id=%s)", result)
        return result
    except Exception as e:
        logger.error("Activity save failed: %s", e)
        raise


async def get_recent_activity(limit: int = 20, category: str | None = None) -> list[dict]:
    """
    Get recent debug activity sorted by newest first.
    Optionally filter by category (ERROR, OPTIMIZATION, REFACTOR, FEATURE).
    """
    db = await get_db()
    try:
        if category:
            cursor = await db.execute(
                """SELECT * FROM debug_activity
                   WHERE UPPER(category) = UPPER(?)
                   ORDER BY created_at DESC LIMIT ?""",
                (category, limit)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM debug_activity ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        rows = await cursor.fetchall()

        activities = []
        for row in rows:
            r = dict(row)
            # Rename error_text to error for frontend compatibility
            r["error"] = r.pop("error_text", "")
            activities.append(r)

        return activities
    finally:
        await db.close()


async def get_activity_by_id(activity_id: int) -> dict | None:
    """Get a single activity by ID."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM debug_activity WHERE id = ?", (activity_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        r = dict(row)
        r["error"] = r.pop("error_text", "")
        return r
    finally:
        await db.close()
