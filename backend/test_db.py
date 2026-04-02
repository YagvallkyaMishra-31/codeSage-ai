import asyncio
import logging

logging.basicConfig(level=logging.INFO)

from app.database.db import init_db

async def test_connection():
    print("Testing connection to Supabase...")
    try:
        await init_db()
        print("\n✅ SUCCESS: Connected to Supabase PostgreSQL and created/verified all tables!")
    except Exception as e:
        print(f"\n❌ FAILED: Error connecting to Supabase: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
