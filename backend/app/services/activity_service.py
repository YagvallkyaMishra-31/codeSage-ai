"""
Activity service: stores and retrieves debug activity records.
"""
from app.database.db import get_db


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
    Returns the activity ID.
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO debug_activity
               (repo_id, error_text, root_cause, explanation, suggested_fix,
                code_patch, severity, category, file_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (repo_id, error_text, root_cause, explanation, suggested_fix,
             code_patch, severity, category, file_path)
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


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
