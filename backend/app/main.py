"""
CodeSage AI — FastAPI Backend
Phase 1: Repository Ingestion & Indexing
Phase 2: Embeddings & Vector Search
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Configure structured logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
from app.config import CORS_ORIGINS
from app.database.db import init_db
from app.api.repo_routes import router as repo_router
from app.api.search_routes import router as search_router
from app.api.debug_routes import router as debug_router
from app.api.activity_routes import router as activity_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    print("✅ Database initialized")
    yield


app = FastAPI(
    title="CodeSage AI API",
    description="AI-powered repository debugging and code analysis platform",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Dynamic CORS Configuration ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount routes ──
app.include_router(repo_router)
app.include_router(search_router)
app.include_router(debug_router)
app.include_router(activity_router)


@app.get("/")
async def root():
    return {
        "service": "CodeSage AI API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
