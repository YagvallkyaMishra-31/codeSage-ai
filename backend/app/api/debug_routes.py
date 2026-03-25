"""
Debug Assistant API routes.
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.debug_service import analyze_issue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/debug", tags=["Debug Assistant"])


class DebugRequest(BaseModel):
    error: str
    repo_id: Optional[int] = None


@router.post("/analyze")
async def debug_analyze(request: DebugRequest):
    """
    Analyze an error using RAG pipeline.
    Retrieves relevant code context from indexed repositories,
    sends to LLM, and returns root cause analysis with suggested fix.
    """
    if not request.error.strip():
        raise HTTPException(status_code=400, detail="Error text is required")

    logger.info("Debug analysis requested (repo_id=%s, error_len=%d)", request.repo_id, len(request.error))

    try:
        result = await analyze_issue(
            error_text=request.error,
            repo_id=request.repo_id,
        )
        logger.info("Debug analysis completed successfully")
        return result
    except ConnectionError as e:
        logger.error("LLM service unavailable: %s", e)
        raise HTTPException(status_code=503, detail="Local LLM service (Ollama) is not running. Please start Ollama and try again.")
    except (ValueError, RuntimeError) as e:
        logger.error("LLM error: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error("Analysis failed unexpectedly: %s", e)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
