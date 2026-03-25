"""
Pydantic models for debug activity records.
"""
from pydantic import BaseModel
from typing import Optional


class DebugActivityResponse(BaseModel):
    id: int
    repo_id: Optional[int] = None
    error: str
    root_cause: Optional[str] = None
    explanation: Optional[str] = None
    suggested_fix: Optional[str] = None
    code_patch: Optional[str] = None
    severity: str
    category: str
    file_path: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
