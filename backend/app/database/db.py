"""
Database layer with automatic backend selection:
  - If DATABASE_URL is set and starts with 'postgresql', uses psycopg3 async.
  - Otherwise, falls back to local SQLite via aiosqlite.

Tables: repositories, file_metadata, code_chunks, debug_activity,
        file_summaries, code_graphs, code_issues
"""
import logging
import os
import aiosqlite
from pathlib import Path
from app.config import DATABASE_URL, DB_PATH

logger = logging.getLogger(__name__)

# Determine which backend to use
USE_POSTGRES = bool(DATABASE_URL) and DATABASE_URL.startswith("postgresql")

# ─────────────────────────────────────────────
# SQLite backend (local development)
# ─────────────────────────────────────────────

SQLITE_TABLES = """
CREATE TABLE IF NOT EXISTS repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    local_path TEXT NOT NULL,
    status TEXT DEFAULT 'cloning',
    total_files INTEGER DEFAULT 0,
    indexed_files INTEGER DEFAULT 0,
    repo_size_bytes INTEGER DEFAULT 0,
    languages TEXT DEFAULT '[]',
    branches INTEGER DEFAULT 1,
    analysis_status TEXT DEFAULT 'pending',
    summary_message TEXT DEFAULT '',
    health_score INTEGER DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS file_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    language TEXT,
    size_bytes INTEGER DEFAULT 0,
    line_count INTEGER DEFAULT 0,
    FOREIGN KEY (repo_id) REFERENCES repositories(id)
);

CREATE TABLE IF NOT EXISTS code_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    FOREIGN KEY (repo_id) REFERENCES repositories(id),
    FOREIGN KEY (file_id) REFERENCES file_metadata(id)
);

CREATE TABLE IF NOT EXISTS debug_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id INTEGER,
    error_text TEXT NOT NULL,
    root_cause TEXT,
    explanation TEXT,
    suggested_fix TEXT,
    code_patch TEXT,
    severity TEXT DEFAULT 'medium',
    category TEXT DEFAULT 'ERROR',
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS file_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    summary TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (repo_id) REFERENCES repositories(id),
    UNIQUE(repo_id, file_path)
);

CREATE TABLE IF NOT EXISTS code_graphs (
    repo_id INTEGER PRIMARY KEY,
    graph_data TEXT NOT NULL,
    FOREIGN KEY (repo_id) REFERENCES repositories(id)
);

CREATE TABLE IF NOT EXISTS code_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    severity TEXT DEFAULT 'medium',
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    fix_suggestion TEXT,
    impact TEXT,
    why_it_matters TEXT,
    line_start INTEGER,
    line_end INTEGER,
    confidence_score REAL DEFAULT 0.8,
    priority_score REAL DEFAULT 0.0,
    is_false_positive INTEGER DEFAULT 0,
    issue_hash TEXT UNIQUE,
    status TEXT DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (repo_id) REFERENCES repositories(id)
);

CREATE INDEX IF NOT EXISTS idx_issues_repo ON code_issues(repo_id);
CREATE INDEX IF NOT EXISTS idx_issues_severity ON code_issues(repo_id, severity);
CREATE INDEX IF NOT EXISTS idx_issues_priority ON code_issues(repo_id, priority_score DESC);
"""


class SQLiteCursorWrapper:
    """Wraps aiosqlite cursor to provide a consistent API."""

    def __init__(self, cursor, lastrowid=None):
        self._cursor = cursor
        self._lastrowid = lastrowid

    @property
    def lastrowid(self):
        return self._lastrowid

    async def fetchone(self):
        return await self._cursor.fetchone()

    async def fetchall(self):
        return await self._cursor.fetchall()


class SQLiteConnectionWrapper:
    """Wraps an aiosqlite connection to provide a consistent API."""

    def __init__(self, conn):
        self._conn = conn
        self.row_factory = None

    async def execute(self, query: str, params=None):
        if params is None:
            cursor = await self._conn.execute(query)
        else:
            cursor = await self._conn.execute(query, params)
        return SQLiteCursorWrapper(cursor, lastrowid=cursor.lastrowid)

    async def commit(self):
        await self._conn.commit()

    async def rollback(self):
        await self._conn.rollback()

    async def close(self):
        await self._conn.close()


async def _init_sqlite():
    """Initialize SQLite database with all tables."""
    logger.info("Initializing SQLite database at %s ...", DB_PATH)
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    try:
        # Enable WAL mode for concurrent read/write support
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
        await db.executescript(SQLITE_TABLES)
        await db.commit()
        logger.info("SQLite database initialized successfully (WAL mode enabled)")
    finally:
        await db.close()


async def _get_sqlite():
    """Return a wrapped SQLite connection with WAL mode."""
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    # WAL mode + busy_timeout on every connection for concurrent safety
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA busy_timeout=5000")
    return SQLiteConnectionWrapper(db)


# ─────────────────────────────────────────────
# PostgreSQL backend (production / Supabase)
# ─────────────────────────────────────────────

if USE_POSTGRES:
    import psycopg
    from psycopg.rows import dict_row

    class CompatRow(dict):
        """
        Row that supports both dict-style (row["col"]) and
        index-style (row[0]) access, mimicking sqlite3.Row behavior.
        """

        def __init__(self, mapping):
            super().__init__(mapping)
            self._ordered_values = list(mapping.values())
            self._ordered_keys = list(mapping.keys())

        def __getitem__(self, key):
            if isinstance(key, int):
                return self._ordered_values[key]
            return super().__getitem__(key)

        def __iter__(self):
            return iter(self._ordered_values)

        def __len__(self):
            return len(self._ordered_values)

        def keys(self):
            return self._ordered_keys

    class CompatCursor:
        def __init__(self, cursor, lastrowid=None):
            self._cursor = cursor
            self._lastrowid = lastrowid

        @property
        def lastrowid(self):
            return self._lastrowid

        async def fetchone(self):
            row = await self._cursor.fetchone()
            if row is None:
                return None
            return CompatRow(row)

        async def fetchall(self):
            rows = await self._cursor.fetchall()
            return [CompatRow(r) for r in rows]

    class CompatConnection:
        def __init__(self, conn):
            self._conn = conn
            self.row_factory = None

        async def execute(self, query: str, params=None):
            pg_query = query.replace("?", "%s")
            is_insert = pg_query.strip().upper().startswith("INSERT")
            has_returning = "RETURNING" in pg_query.upper()

            if params is None:
                cursor = await self._conn.execute(pg_query)
            else:
                cursor = await self._conn.execute(pg_query, params)

            lastrowid = None
            if is_insert and has_returning:
                try:
                    row = await cursor.fetchone()
                    if row:
                        lastrowid = list(row.values())[0] if isinstance(row, dict) else row[0]
                except Exception:
                    pass

            return CompatCursor(cursor, lastrowid=lastrowid)

        async def commit(self):
            await self._conn.commit()

        async def rollback(self):
            await self._conn.rollback()

        async def close(self):
            await self._conn.close()

    PG_TABLES = """
        CREATE TABLE IF NOT EXISTS repositories (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            local_path TEXT NOT NULL,
            status TEXT DEFAULT 'cloning',
            total_files INTEGER DEFAULT 0,
            indexed_files INTEGER DEFAULT 0,
            repo_size_bytes INTEGER DEFAULT 0,
            languages TEXT DEFAULT '[]',
            branches INTEGER DEFAULT 1,
            analysis_status TEXT DEFAULT 'pending',
            summary_message TEXT DEFAULT '',
            health_score INTEGER DEFAULT 100,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS file_metadata (
            id SERIAL PRIMARY KEY,
            repo_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            language TEXT,
            size_bytes INTEGER DEFAULT 0,
            line_count INTEGER DEFAULT 0,
            FOREIGN KEY (repo_id) REFERENCES repositories(id)
        );
        CREATE TABLE IF NOT EXISTS code_chunks (
            id SERIAL PRIMARY KEY,
            repo_id INTEGER NOT NULL,
            file_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            start_line INTEGER,
            end_line INTEGER,
            FOREIGN KEY (repo_id) REFERENCES repositories(id),
            FOREIGN KEY (file_id) REFERENCES file_metadata(id)
        );
        CREATE TABLE IF NOT EXISTS debug_activity (
            id SERIAL PRIMARY KEY,
            repo_id INTEGER,
            error_text TEXT NOT NULL,
            root_cause TEXT,
            explanation TEXT,
            suggested_fix TEXT,
            code_patch TEXT,
            severity TEXT DEFAULT 'medium',
            category TEXT DEFAULT 'ERROR',
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS file_summaries (
            id SERIAL PRIMARY KEY,
            repo_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            summary TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (repo_id) REFERENCES repositories(id),
            UNIQUE(repo_id, file_path)
        );
        CREATE TABLE IF NOT EXISTS code_graphs (
            repo_id INTEGER PRIMARY KEY,
            graph_data TEXT NOT NULL,
            FOREIGN KEY (repo_id) REFERENCES repositories(id)
        );
        CREATE TABLE IF NOT EXISTS code_issues (
            id SERIAL PRIMARY KEY,
            repo_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            severity TEXT DEFAULT 'medium',
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            fix_suggestion TEXT,
            impact TEXT,
            why_it_matters TEXT,
            line_start INTEGER,
            line_end INTEGER,
            confidence_score REAL DEFAULT 0.8,
            priority_score REAL DEFAULT 0.0,
            is_false_positive INTEGER DEFAULT 0,
            issue_hash TEXT UNIQUE,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (repo_id) REFERENCES repositories(id)
        );
        CREATE INDEX IF NOT EXISTS idx_issues_repo ON code_issues(repo_id);
        CREATE INDEX IF NOT EXISTS idx_issues_severity ON code_issues(repo_id, severity);
        CREATE INDEX IF NOT EXISTS idx_issues_priority ON code_issues(repo_id, priority_score DESC);
    """

    async def _init_postgres():
        logger.info("Initializing PostgreSQL database...")
        conn = await psycopg.AsyncConnection.connect(
            DATABASE_URL, row_factory=dict_row, autocommit=True,
            prepare_threshold=None,
        )
        try:
            for statement in PG_TABLES.split(";"):
                statement = statement.strip()
                if statement:
                    await conn.execute(statement)
            logger.info("PostgreSQL database initialized successfully")
        finally:
            await conn.close()

    async def _get_postgres():
        conn = await psycopg.AsyncConnection.connect(
            DATABASE_URL, row_factory=dict_row, autocommit=False,
            prepare_threshold=None,
        )
        return CompatConnection(conn)


# ─────────────────────────────────────────────
# Public API — auto-dispatches to the right backend
# ─────────────────────────────────────────────

async def init_db():
    if USE_POSTGRES:
        await _init_postgres()
    else:
        await _init_sqlite()


async def get_db():
    if USE_POSTGRES:
        return await _get_postgres()
    else:
        return await _get_sqlite()
