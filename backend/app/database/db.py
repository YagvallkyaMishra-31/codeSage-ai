"""
SQLite database layer using aiosqlite for async operations.
Tables: repositories, file_metadata, code_chunks
"""
import aiosqlite
from app.config import DB_PATH


async def init_db():
    """Create tables if they don't exist."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS file_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                language TEXT,
                size_bytes INTEGER DEFAULT 0,
                line_count INTEGER DEFAULT 0,
                FOREIGN KEY (repo_id) REFERENCES repositories(id)
            )
        """)
        await db.execute("""
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
            )
        """)
        await db.execute("""
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
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS code_graphs (
                repo_id INTEGER PRIMARY KEY,
                graph_data TEXT NOT NULL,
                FOREIGN KEY (repo_id) REFERENCES repositories(id)
            )
        """)
        await db.commit()


async def get_db():
    """Get an async database connection."""
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    return db
