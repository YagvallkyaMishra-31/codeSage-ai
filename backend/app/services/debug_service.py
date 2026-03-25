"""
Debug service: orchestrates the RAG pipeline for debugging.
Retrieves context → builds prompt → calls LLM → returns analysis.
"""
import logging
import time
from app.services.search_service import semantic_search, get_graph_context_for_files
from app.rag.prompt_builder import build_debug_prompt
from app.rag.llm_client import analyze_debug_issue
from app.services.activity_service import save_activity

logger = logging.getLogger(__name__)


async def analyze_issue(error_text: str, repo_id: int | None = None) -> dict:
    """
    Full debug analysis pipeline:
    1. Semantic search for relevant code chunks
    2. Build a structured prompt with error + context
    3. Send to LLM for analysis
    4. Return structured response

    Args:
        error_text: Error message, stack trace, or code snippet
        repo_id: Optional repo ID to scope search

    Returns:
        Dict with root_cause, explanation, suggested_fix, code_patch, etc.
    """
    # Step 1: Retrieve relevant code context (top 5)
    logger.info("Starting debug analysis pipeline (repo_id=%s)", repo_id)
    retrieved_chunks = await semantic_search(
        query=error_text,
        top_k=5,
        repo_id=repo_id,
    )
    logger.info("Semantic search returned %d chunks", len(retrieved_chunks))

    # Step 1.5: Retrieve graph context for those files
    graph_context = {}
    if repo_id and retrieved_chunks:
        # Extract unique file paths
        file_paths = list({c["file_path"] for c in retrieved_chunks})
        graph_context = await get_graph_context_for_files(repo_id, file_paths)

    # Step 2: Build prompt
    messages = build_debug_prompt(error_text, retrieved_chunks, graph_context)

    # Step 3: Call LLM
    t0 = time.perf_counter()
    result = await analyze_debug_issue(messages)
    elapsed = time.perf_counter() - t0
    logger.info("LLM analysis completed in %.1fs", elapsed)

    # Step 4: Save activity record asynchronously
    try:
        primary_file = result.get("related_files", [""])[0] if result.get("related_files") else ""
        await save_activity(
            error_text=error_text,
            root_cause=result.get("root_cause", ""),
            explanation=result.get("explanation", ""),
            suggested_fix=result.get("suggested_fix", ""),
            code_patch=result.get("code_patch", ""),
            severity=result.get("severity", "medium"),
            category=result.get("category", "ERROR"),
            file_path=primary_file,
            repo_id=repo_id
        )
        logger.info("Activity record saved")
    except Exception as e:
        logger.warning("Failed to save activity: %s", e)

    # Step 5: Enrich response with retrieved context info
    result["context_used"] = [
        {
            "file_path": c["file_path"],
            "language": c.get("language", "Unknown"),
            "score": c.get("score", 0),
        }
        for c in retrieved_chunks
    ]
    
    result["dependency_context"] = graph_context

    return result
