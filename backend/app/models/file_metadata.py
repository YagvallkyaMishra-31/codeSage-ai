"""
Pydantic models for file metadata.
"""
from pydantic import BaseModel


class FileMetadataResponse(BaseModel):
    id: int
    repo_id: int
    file_name: str
    file_path: str
    language: str
    size_bytes: int
    line_count: int

    class Config:
        from_attributes = True
