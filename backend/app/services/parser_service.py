"""
Parser service: scan repository files, extract metadata.
"""
import os
from pathlib import Path
from app.config import ALLOWED_EXTENSIONS, IGNORED_DIRS, EXTENSION_LANGUAGE_MAP


def scan_repository(local_path: str) -> list[dict]:
    """
    Walk the repository directory tree and extract metadata
    for all code files matching allowed extensions.
    
    Returns a list of dicts:
      { file_name, file_path, language, size_bytes, line_count }
    """
    files = []
    root = Path(local_path)

    for dirpath, dirnames, filenames in os.walk(root):
        # Remove ignored directories in-place so os.walk skips them
        dirnames[:] = [
            d for d in dirnames
            if d not in IGNORED_DIRS
        ]

        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue

            full_path = Path(dirpath) / fname
            relative_path = full_path.relative_to(root)

            try:
                size_bytes = full_path.stat().st_size
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    line_count = sum(1 for _ in f)
            except Exception:
                size_bytes = 0
                line_count = 0

            files.append({
                "file_name": fname,
                "file_path": str(relative_path),
                "language": EXTENSION_LANGUAGE_MAP.get(ext, "Unknown"),
                "size_bytes": size_bytes,
                "line_count": line_count,
            })

    return files


def detect_languages(files: list[dict]) -> list[str]:
    """Extract unique languages from parsed file list."""
    languages = set()
    for f in files:
        if f["language"] != "Unknown":
            languages.add(f["language"])
    return sorted(languages)


def calculate_repo_size(files: list[dict]) -> int:
    """Sum up total bytes across all scanned files."""
    return sum(f["size_bytes"] for f in files)
