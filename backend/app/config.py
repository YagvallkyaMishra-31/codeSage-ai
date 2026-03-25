import os
from pathlib import Path

# ── Paths ──
BASE_DIR = Path(__file__).resolve().parent.parent
REPOS_DIR = BASE_DIR / "repos"
DB_PATH = BASE_DIR / "data" / "codesage.db"

# Ensure directories exist
REPOS_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Dynamic Environment Variables ──
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Parse CORS origins from a comma-separated string
raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
CORS_ORIGINS = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

# ── Allowed Code Extensions ──
ALLOWED_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".go", ".cpp", ".c", ".h",
    ".rs", ".rb", ".php", ".swift", ".kt",
    ".scala", ".cs", ".vue", ".svelte",
}

# ── Ignored Directories ──
IGNORED_DIRS = {
    "node_modules", ".git", "build", "dist",
    "__pycache__", ".venv", "venv", ".next",
    ".cache", "coverage", ".idea", ".vscode",
    "target", "bin", "obj",
}

# ── Extension → Language mapping ──
EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".java": "Java",
    ".go": "Go",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".cs": "C#",
    ".vue": "Vue",
    ".svelte": "Svelte",
}

# ── Chunking config ──
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
