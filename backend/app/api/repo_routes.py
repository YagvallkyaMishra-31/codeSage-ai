"""
Repository API routes.
"""
import logging
from fastapi import APIRouter, HTTPException
from app.models.repository import RepoConnectRequest, RepoResponse, RepoStatusResponse
from app.services.repo_service import (
    connect_repository, list_repositories, get_repository_status,
    DuplicateRepositoryError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/repository", tags=["Repository"])


@router.post("/connect")
async def connect_repo(request: RepoConnectRequest):
    """
    Clone a GitHub repository and start the indexing pipeline.
    Returns the repository record immediately while indexing runs in background.
    """
    # Validate URL format
    url = request.repo_url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid repository URL. Must start with http:// or https://")

    try:
        repo = await connect_repository(url)
        logger.info("Repository connected: %s", url)
        return {
            "message": "Repository connected successfully. Indexing started.",
            "repository": repo,
        }
    except DuplicateRepositoryError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error("Failed to connect repository %s: %s", url, e)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list")
async def list_repos():
    """Return all indexed repositories."""
    repos = await list_repositories()
    return {"repositories": repos}


@router.get("/{repo_id}/status")
async def repo_status(repo_id: int):
    """
    Get indexing progress for a repository.
    Includes: files scanned, files indexed, languages, progress %.
    """
    status = await get_repository_status(repo_id)
    if not status:
        raise HTTPException(status_code=404, detail="Repository not found")
    return status
