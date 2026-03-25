"""
Embedding service using SentenceTransformers.
Loads the model once and provides a function to generate embeddings.
"""
import numpy as np
from sentence_transformers import SentenceTransformer

# Load model once at module level (lazy singleton)
_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print("🔄 Loading embedding model (all-MiniLM-L6-v2)...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        print("✅ Embedding model loaded")
    return _model


def generate_embedding(text: str) -> np.ndarray:
    """Generate a single embedding vector for the given text."""
    model = _get_model()
    return model.encode(text, normalize_embeddings=True)


def generate_embeddings_batch(texts: list[str]) -> np.ndarray:
    """Generate embeddings for a batch of texts (more efficient)."""
    model = _get_model()
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def get_embedding_dimension() -> int:
    """Return the dimension of the embedding vectors."""
    model = _get_model()
    return model.get_sentence_embedding_dimension()
