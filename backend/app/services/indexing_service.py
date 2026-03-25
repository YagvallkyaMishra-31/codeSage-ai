"""
Indexing service: background pipeline that scans files,
chunks code, generates embeddings, and stores everything.
Updates progress for status polling.
"""
import json
import asyncio
import logging
from pathlib import Path

from app.database.db import get_db
from app.services.parser_service import scan_repository, detect_languages, calculate_repo_size
from app.rag.chunking import chunk_code
from app.rag.embeddings import generate_embeddings_batch
from app.rag.vector_store import add_to_vector_store
from app.services.code_graph_service import build_code_graph

logger = logging.getLogger(__name__)


async def run_indexing_pipeline(repo_id: int, local_path: str):
    """
    Background indexing pipeline:
    1. Scan repository for code files
    2. Update repo metadata (total_files, languages, size)
    3. For each file: parse → chunk → store in DB
    4. Generate embeddings and store in FAISS vector DB
    5. Update progress as we go
    """
    db = await get_db()

    try:
        # ── Step 1: Scan files ──
        logger.info("Indexing pipeline started for repo_id=%d, path=%s", repo_id, local_path)
        await db.execute(
            "UPDATE repositories SET status = 'scanning' WHERE id = ?",
            (repo_id,)
        )
        await db.commit()

        files = scan_repository(local_path)
        languages = detect_languages(files)
        repo_size = calculate_repo_size(files)

        # ── Step 2: Update repo metadata ──
        await db.execute(
            """UPDATE repositories
               SET total_files = ?, languages = ?, repo_size_bytes = ?, status = 'indexing'
               WHERE id = ?""",
            (len(files), json.dumps(languages), repo_size, repo_id)
        )
        await db.commit()

        # ── Step 3: Index each file ──
        # Collect chunks in batches for efficient embedding
        batch_chunks = []
        batch_meta = []
        BATCH_SIZE = 32

        for i, file_info in enumerate(files):
            # Insert file metadata
            cursor = await db.execute(
                """INSERT INTO file_metadata (repo_id, file_name, file_path, language, size_bytes, line_count)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (repo_id, file_info["file_name"], file_info["file_path"],
                 file_info["language"], file_info["size_bytes"], file_info["line_count"])
            )
            file_id = cursor.lastrowid

            # Read file content and chunk it
            full_path = Path(local_path) / file_info["file_path"]
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                chunks = chunk_code(content)

                for chunk_idx, chunk_text in enumerate(chunks):
                    await db.execute(
                        """INSERT INTO code_chunks (repo_id, file_id, chunk_index, content)
                           VALUES (?, ?, ?, ?)""",
                        (repo_id, file_id, chunk_idx, chunk_text)
                    )

                    # Collect for batch embedding
                    batch_chunks.append(chunk_text)
                    batch_meta.append({
                        "file_path": file_info["file_path"],
                        "language": file_info["language"],
                        "chunk_text": chunk_text,
                        "chunk_index": chunk_idx,
                    })

                    # Process batch when full
                    if len(batch_chunks) >= BATCH_SIZE:
                        await _embed_and_store_batch(repo_id, batch_chunks, batch_meta)
                        batch_chunks = []
                        batch_meta = []

            except Exception:
                pass  # Skip unreadable files

            # Update progress
            await db.execute(
                "UPDATE repositories SET indexed_files = ? WHERE id = ?",
                (i + 1, repo_id)
            )
            await db.commit()

            # Yield control to event loop
            await asyncio.sleep(0)

        # Process remaining chunks
        if batch_chunks:
            await _embed_and_store_batch(repo_id, batch_chunks, batch_meta)

        # ── Step 4: Build and Store Code Graph ──
        # Build the dependency graph using the file paths
        try:
            graph_data = build_code_graph(local_path)
            
            # Upsert into code_graphs table
            await db.execute(
                """INSERT OR REPLACE INTO code_graphs (repo_id, graph_data) 
                   VALUES (?, ?)""",
                (repo_id, json.dumps(graph_data))
            )
            await db.commit()
        except Exception as e:
            logger.warning("Failed to build Code Graph for repo %d: %s", repo_id, e)

        # ── Step 5: Mark complete ──
        logger.info("Indexing pipeline completed for repo_id=%d (%d files)", repo_id, len(files))
        await db.execute(
            "UPDATE repositories SET status = 'completed', indexed_files = total_files WHERE id = ?",
            (repo_id,)
        )
        await db.commit()

    except Exception as e:
        logger.error("Indexing pipeline FAILED for repo_id=%d: %s", repo_id, e)
        await db.execute(
            "UPDATE repositories SET status = 'failed' WHERE id = ?",
            (repo_id,)
        )
        await db.commit()
        raise e
    finally:
        await db.close()


async def _embed_and_store_batch(repo_id: int, texts: list[str], metadata: list[dict]):
    """Generate embeddings for a batch and store in FAISS."""
    loop = asyncio.get_event_loop()
    embeddings = await loop.run_in_executor(None, generate_embeddings_batch, texts)
    add_to_vector_store(repo_id, metadata, embeddings)
