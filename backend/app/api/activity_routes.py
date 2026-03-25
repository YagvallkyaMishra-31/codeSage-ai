"""
Activity API routes.
"""
import logging
from fastapi import APIRouter, HTTPException
from typing import Optional
from app.services.activity_service import get_recent_activity, get_activity_by_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Activity"])


@router.get("/activity")
async def list_activity(limit: int = 20, category: Optional[str] = None):
    """
    Get recent debug activity.
    Optional query params: limit (default 20), category (ERROR, OPTIMIZATION, REFACTOR, FEATURE)
    """
    logger.info("Fetching activity (limit=%d, category=%s)", limit, category)
    activities = await get_recent_activity(limit=limit, category=category)
    return {"activities": activities}


@router.get("/activity/{activity_id}")
async def get_activity(activity_id: int):
    """Get a single activity by ID with full details."""
    activity = await get_activity_by_id(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity
