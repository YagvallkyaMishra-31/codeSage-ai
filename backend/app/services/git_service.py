"""
Git service: clone repositories using GitPython.
"""
import os
import stat
import shutil
import logging
from pathlib import Path
from git import Repo
from app.config import REPOS_DIR

logger = logging.getLogger(__name__)


def _remove_readonly(func, path, _exc_info):
    """Handle read-only files on Windows during shutil.rmtree."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def clone_repository(repo_url: str) -> tuple[str, str]:
    """
    Clone a git repository and return (repo_name, local_path).
    If the repo already exists locally, remove it first for a fresh clone.
    """
    # Extract repo name from URL
    repo_name = repo_url.rstrip("/").split("/")[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    local_path = REPOS_DIR / repo_name

    # Remove existing clone if present (Windows-safe)
    if local_path.exists():
        logger.info("Removing existing clone at %s", local_path)
        shutil.rmtree(local_path, onerror=_remove_readonly)

    # Clone — depth=1 for speed (shallow clone)
    logger.info("Cloning %s → %s", repo_url, local_path)
    Repo.clone_from(repo_url, str(local_path), depth=1)
    logger.info("Clone complete: %s", repo_name)

    return repo_name, str(local_path)


def get_branch_count(local_path: str) -> int:
    """Count remote branches."""
    try:
        repo = Repo(local_path)
        return len(repo.remotes.origin.refs)
    except Exception:
        return 1
