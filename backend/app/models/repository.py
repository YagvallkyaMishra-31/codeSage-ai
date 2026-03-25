"""
Pydantic models for repository requests and responses.
"""
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


class RepoConnectRequest(BaseModel):
    repo_url: str


class RepoResponse(BaseModel):
    id: int
    name: str
    url: str
    status: str
    total_files: int
    indexed_files: int
    repo_size_bytes: int
    languages: str  # JSON string list
    branches: int
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class RepoStatusResponse(BaseModel):
    id: int
    name: str
    status: str
    total_files: int
    indexed_files: int
    languages: str
    progress_percent: float
    repo_size_bytes: int
