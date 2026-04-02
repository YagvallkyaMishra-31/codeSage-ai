"""
PostgreSQL database layer using psycopg3 for async operations.
Provides a compatibility wrapper that mimics the aiosqlite API,
so all service files continue to work with minimal modifications.

Tables: repositories, file_metadata, code_chunks, debug_activity,
        file_summaries, code_graphs, code_issues
"""
import logging
import psycopg
from psycopg.rows import dict_row
from app.config import DATABASE_URL

logger = logging.getLogger(__name__)


class CompatRow(dict):
    """
    Row that supports both dict-style (row["col"]) and
    index-style (row[0]) access, mimicking sqlite3.Row behavior.
    Also supports dict(list_of_rows) for aggregation queries.
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
        """Iterate over VALUES (not keys) to mimic sqlite3.Row.
        This allows dict(list_of_rows) to work for aggregation queries
        like: dict(await cursor.fetchall())  on SELECT col, COUNT(*) ... GROUP BY col
        """
        return iter(self._ordered_values)

    def __len__(self):
        return len(self._ordered_values)

    def keys(self):
        return self._ordered_keys


class CompatCursor:
    """
    Wraps a psycopg cursor to mimic aiosqlite's cursor API.
    Supports .lastrowid, .fetchone(), .fetchall().
    """

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
    """
    Wraps a psycopg async connection to mimic aiosqlite's API.
    Auto-converts ? placeholders to %s for PostgreSQL.
    """

    def __init__(self, conn):
        self._conn = conn
        self.row_factory = None  # Ignored; always dict_row

    async def execute(self, query: str, params=None):
        # Convert ? placeholders to %s (PostgreSQL paramstyle)
        pg_query = query.replace("?", "%s")

        # Detect INSERT with RETURNING (for lastrowid)
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
                    # Get the first value (should be id)
                    lastrowid = list(row.values())[0] if isinstance(row, dict) else row[0]
            except Exception:
                pass

        return CompatCursor(cursor, lastrowid=lastrowid)

    async def commit(self):
        await self._conn.commit()

    async def close(self):
        await self._conn.close()


async def init_db():
    """Create tables if they don't exist (PostgreSQL-compatible DDL)."""
    logger.info("Initializing PostgreSQL database...")
    conn = await psycopg.AsyncConnection.connect(
        DATABASE_URL, row_factory=dict_row, autocommit=True
    )
    try:
        await conn.execute("""
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
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS file_metadata (
                id SERIAL PRIMARY KEY,
                repo_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                language TEXT,
                size_bytes INTEGER DEFAULT 0,
                line_count INTEGER DEFAULT 0,
                FOREIGN KEY (repo_id) REFERENCES repositories(id)
            )
        """)
        await conn.execute("""
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
            )
        """)
        await conn.execute("""
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
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS file_summaries (
                id SERIAL PRIMARY KEY,
                repo_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                summary TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (repo_id) REFERENCES repositories(id),
                UNIQUE(repo_id, file_path)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS code_graphs (
                repo_id INTEGER PRIMARY KEY,
                graph_data TEXT NOT NULL,
                FOREIGN KEY (repo_id) REFERENCES repositories(id)
            )
        """)
        await conn.execute("""
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
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_issues_repo ON code_issues(repo_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_issues_severity ON code_issues(repo_id, severity)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_issues_priority ON code_issues(repo_id, priority_score DESC)
        """)
        logger.info("PostgreSQL database initialized successfully")
    finally:
        await conn.close()


async def get_db():
    """Get an async database connection wrapped for compatibility."""
    conn = await psycopg.AsyncConnection.connect(
        DATABASE_URL, row_factory=dict_row, autocommit=False
    )
    return CompatConnection(conn)
