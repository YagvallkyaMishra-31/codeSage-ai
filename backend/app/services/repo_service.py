"""
Repo service: orchestrates clone → DB record → background indexing.
"""
import asyncio
import json
import logging
from app.database.db import get_db
from app.services.git_service import clone_repository, get_branch_count
from app.services.indexing_service import run_indexing_pipeline

logger = logging.getLogger(__name__)


class DuplicateRepositoryError(Exception):
    """Raised when a repository URL is already indexed."""
    pass


async def connect_repository(repo_url: str) -> dict:
    """
    Full pipeline:
    1. Check for duplicate URL
    2. Clone the repo (sync, runs in thread pool)
    3. Create a DB record
    4. Launch background indexing task
    5. Return the repo record immediately
    """
    # Check for duplicate
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, name FROM repositories WHERE url = ?", (repo_url,)
        )
        existing = await cursor.fetchone()
        if existing:
            raise DuplicateRepositoryError(
                f"Repository '{existing['name']}' is already indexed (id={existing['id']})"
            )
    finally:
        await db.close()

    # Clone in a thread pool so we don't block the event loop
    logger.info("Connecting repository: %s", repo_url)
    loop = asyncio.get_event_loop()
    repo_name, local_path = await loop.run_in_executor(
        None, clone_repository, repo_url
    )

    branches = await loop.run_in_executor(
        None, get_branch_count, local_path
    )

    # Create DB record
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO repositories (name, url, local_path, status, branches)
               VALUES (?, ?, ?, 'scanning', ?)""",
            (repo_name, repo_url, local_path, branches)
        )
        await db.commit()
        repo_id = cursor.lastrowid

        # Fetch the created record
        row = await db.execute(
            "SELECT * FROM repositories WHERE id = ?", (repo_id,)
        )
        repo = await row.fetchone()
    finally:
        await db.close()

    logger.info("Repository record created: id=%d, name=%s", repo_id, repo_name)

    # Launch background indexing (fire and forget)
    asyncio.create_task(run_indexing_pipeline(repo_id, local_path))

    return dict(repo)


async def list_repositories() -> list[dict]:
    """Return all repositories."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM repositories ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_repository_status(repo_id: int) -> dict | None:
    """Get repository with computed progress percentage."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM repositories WHERE id = ?", (repo_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None

        repo = dict(row)
        total = repo["total_files"] or 1
        indexed = repo["indexed_files"] or 0
        repo["progress_percent"] = round((indexed / total) * 100, 1)
        return repo
    finally:
        await db.close()
