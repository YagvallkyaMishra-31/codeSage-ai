"""
Embedding service using SentenceTransformers.
Loads the model once and provides a function to generate embeddings.
"""
import os
# VERY IMPORTANT: Prevent OpenMP deadlock on Windows between PyTorch and Faiss
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_OK"] = "TRUE"

import numpy as np

# Load model once at module level (lazy singleton)
_model = None


import logging
logger = logging.getLogger(__name__)

def _get_model():
    global _model
    if _model is None:
        logger.info("Loading embedding model (all-MiniLM-L6-v2)...")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        logger.info("Embedding model loaded successfully")
    return _model


def generate_embedding(text: str) -> np.ndarray:
    """Generate a single embedding vector for the given text."""
    model = _get_model()
    return model.encode(text, normalize_embeddings=True)


def generate_embeddings_batch(texts: list[str]) -> np.ndarray:
    """Generate embeddings for a batch of texts (more efficient)."""
    logger.info("Generating embeddings for batch of size %d...", len(texts))
    model = _get_model()
    result = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    logger.info("Finished batch.")
    return result


def get_embedding_dimension() -> int:
    """Return the dimension of the embedding vectors."""
    model = _get_model()
    return model.get_sentence_embedding_dimension()
