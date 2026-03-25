"""
Search API routes.
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.search_service import semantic_search

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Search"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    repo_id: Optional[int] = None


@router.post("/search")
async def search_code(request: SearchRequest):
    """
    Semantic code search across indexed repositories.
    Returns the most relevant code chunks matching the query.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    logger.info("Search request: query='%s', top_k=%d, repo_id=%s", request.query[:80], request.top_k, request.repo_id)

    results = await semantic_search(
        query=request.query,
        top_k=request.top_k,
        repo_id=request.repo_id,
    )

    logger.info("Search returned %d results", len(results))
    return {
        "query": request.query,
        "results": results,
        "total": len(results),
    }
