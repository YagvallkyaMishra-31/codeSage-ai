"""Quick test: verify Supabase PostgreSQL connection works."""
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
import os

load_dotenv()

async def test():
    url = os.getenv("DATABASE_URL", "")
    print(f"DATABASE_URL: {url[:60]}...")
    
    if not url:
        print("ERROR: DATABASE_URL is empty!")
        return
    
    try:
        conn = await psycopg.AsyncConnection.connect(
            url, row_factory=dict_row, autocommit=True,
            prepare_threshold=None,
        )
        print("Connected successfully!")
        
        result = await conn.execute("SELECT version()")
        row = await result.fetchone()
        version = list(row.values())[0]
        print(f"PostgreSQL version: {version[:80]}")
        
        # Test creating tables (same as init_db)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                local_path TEXT NOT NULL,
                status TEXT DEFAULT 'cloning',
                total_files INTEGER DEFAULT 0,
                indexed_files INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Table 'repositories' OK")
        
        # Check table exists
        result = await conn.execute(
            "SELECT COUNT(*) as cnt FROM information_schema.tables WHERE table_name = 'repositories'"
        )
        row = await result.fetchone()
        print(f"Table exists: {row['cnt'] > 0}")
        
        await conn.close()
        print("\nAll tests PASSED! Database is ready for deployment.")
    except Exception as e:
        print(f"\nERROR: {e}")

asyncio.run(test())
