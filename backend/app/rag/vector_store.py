"""
FAISS vector store for semantic code search.
Stores embeddings with metadata for retrieval.
"""
import os
import json
import numpy as np
from pathlib import Path
from app.config import BASE_DIR
from app.rag.embeddings import get_embedding_dimension

VECTOR_DB_DIR = BASE_DIR / "vector_db"
VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)


def _index_path(repo_id: int) -> str:
    return str(VECTOR_DB_DIR / f"repo_{repo_id}.index")


def _metadata_path(repo_id: int) -> str:
    return str(VECTOR_DB_DIR / f"repo_{repo_id}_meta.json")


def create_vector_store(repo_id: int, chunks: list[dict], embeddings: np.ndarray):
    """
    Create a FAISS index for a repository.

    Args:
        repo_id: Repository ID
        chunks: List of dicts with keys: file_path, language, chunk_text, chunk_index
        embeddings: numpy array of shape (n_chunks, embedding_dim)
    """
    if len(chunks) == 0:
        return

    import faiss
    dim = embeddings.shape[1]

    # Create FAISS index (Inner Product for cosine similarity with normalized vectors)
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype(np.float32))

    # Save index
    faiss.write_index(index, _index_path(repo_id))

    # Save metadata alongside
    with open(_metadata_path(repo_id), "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)


def add_to_vector_store(repo_id: int, chunks: list[dict], embeddings: np.ndarray):
    """
    Add new chunks to an existing FAISS index, or create one if it doesn't exist.
    """
    index_file = _index_path(repo_id)
    meta_file = _metadata_path(repo_id)

    import faiss
    if os.path.exists(index_file) and os.path.exists(meta_file):
        # Load existing
        index = faiss.read_index(index_file)
        with open(meta_file, "r", encoding="utf-8") as f:
            existing_meta = json.load(f)

        # Append
        index.add(embeddings.astype(np.float32))
        existing_meta.extend(chunks)

        faiss.write_index(index, index_file)
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(existing_meta, f, ensure_ascii=False)
    else:
        create_vector_store(repo_id, chunks, embeddings)


def search_vector_store(repo_id: int, query_embedding: np.ndarray, top_k: int = 5) -> list[dict]:
    """
    Search the FAISS index for similar code chunks.

    Returns list of dicts with: file_path, language, chunk_text, score
    """
    index_file = _index_path(repo_id)
    meta_file = _metadata_path(repo_id)

    if not os.path.exists(index_file) or not os.path.exists(meta_file):
        return []

    import faiss
    index = faiss.read_index(index_file)
    with open(meta_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Search
    query_vec = query_embedding.reshape(1, -1).astype(np.float32)
    scores, indices = index.search(query_vec, min(top_k, index.ntotal))

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(metadata):
            continue
        meta = metadata[idx]
        results.append({
            "file_path": meta["file_path"],
            "language": meta["language"],
            "chunk": meta["chunk_text"],
            "score": round(float(score), 4),
        })

    return results


def search_all_repos(query_embedding: np.ndarray, top_k: int = 5) -> list[dict]:
    """Search across ALL repository vector stores."""
    all_results = []

    for f in VECTOR_DB_DIR.glob("repo_*.index"):
        repo_id = int(f.stem.split("_")[1])
        results = search_vector_store(repo_id, query_embedding, top_k)
        for r in results:
            r["repo_id"] = repo_id
        all_results.extend(results)

    # Sort by score descending, return top_k
    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results[:top_k]
