import asyncio
import logging
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Setup logging to see everything
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)

# This import triggers config.py which loads .env
from app.services.analysis_service import safe_analysis
from app.database.db import get_db

async def main():
    print("="*60)
    print("STARTING DIRECT ANALYSIS TEST")
    print("="*60)
    
    # Check what repos exist
    db = await get_db()
    cursor = await db.execute("SELECT id, name, analysis_status FROM repositories")
    repos = await cursor.fetchall()
    print(f"Available repos: {repos}")
    await db.close()
    
    if not repos:
        print("ERROR: No repositories found! Index one first.")
        return
    
    repo_id = repos[0][0]
    print(f"\nTriggering safe_analysis({repo_id})...")
    await safe_analysis(repo_id)
    
    # Check results
    db = await get_db()
    cursor = await db.execute(
        "SELECT analysis_status, summary_message, health_score FROM repositories WHERE id=?",
        (repo_id,)
    )
    result = await cursor.fetchone()
    print(f"\n{'='*60}")
    print(f"RESULT: status={result[0]}, health={result[2]}")
    print(f"Summary: {result[1]}")
    
    # Count issues
    cursor2 = await db.execute(
        "SELECT COUNT(*) FROM code_issues WHERE repo_id=?",
        (repo_id,)
    )
    count = (await cursor2.fetchone())[0]
    print(f"Total issues in DB: {count}")
    
    if count > 0:
        cursor3 = await db.execute(
            "SELECT severity, title FROM code_issues WHERE repo_id=? LIMIT 5",
            (repo_id,)
        )
        for row in await cursor3.fetchall():
            print(f"  [{row[0]}] {row[1]}")
    
    await db.close()
    print(f"{'='*60}")
    print("TEST COMPLETE")

if __name__ == "__main__":
    asyncio.run(main())
