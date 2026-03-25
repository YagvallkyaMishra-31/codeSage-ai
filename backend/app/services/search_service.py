"""
Search service: semantic code search across indexed repositories.
"""
import json
from app.database.db import get_db
from app.rag.embeddings import generate_embedding
from app.rag.vector_store import search_all_repos, search_vector_store


async def semantic_search(query: str, top_k: int = 5, repo_id: int | None = None) -> list[dict]:
    """
    Perform semantic search over indexed code.

    Args:
        query: Natural language search query
        top_k: Number of results to return
        repo_id: Optional repo ID to scope search to a single repo

    Returns:
        List of matching code chunks with scores
    """
    # Generate query embedding
    query_embedding = generate_embedding(query)

    # Search
    if repo_id:
        results = search_vector_store(repo_id, query_embedding, top_k)
        for r in results:
            r["repo_id"] = repo_id
    else:
        results = search_all_repos(query_embedding, top_k)

    return results


async def get_graph_context_for_files(repo_id: int, file_paths: list[str]) -> dict:
    """
    Fetch the code graph for a repo and extract only the subgraph 
    relevant to the specified file_paths.
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT graph_data FROM code_graphs WHERE repo_id = ?",
            (repo_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return {}
            
        full_graph = json.loads(row["graph_data"])
    finally:
        await db.close()

    # Filter to only the requested files
    subgraph = {}
    for path in file_paths:
        # Normalize path separators
        norm_path = path.replace("\\", "/")
        
        # Try finding exact match or ignoring leading dot
        if norm_path in full_graph:
            subgraph[path] = full_graph[norm_path]
        else:
            # Maybe path in full_graph has leading slash or dot
            for graph_file, data in full_graph.items():
                if graph_file.endswith(norm_path) or norm_path.endswith(graph_file):
                    subgraph[path] = data
                    break

    return subgraph
