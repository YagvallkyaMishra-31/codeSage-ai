"""
Code chunking using LangChain RecursiveCharacterTextSplitter.
Prepares code for later embedding (Phase 2).
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import CHUNK_SIZE, CHUNK_OVERLAP

# Language-aware separators for better code chunking
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=[
        "\nclass ",
        "\ndef ",
        "\n\ndef ",
        "\n\n",
        "\n",
        " ",
        "",
    ],
)


def chunk_code(source_code: str) -> list[str]:
    """
    Split source code into chunks suitable for embedding.
    Returns a list of text chunks.
    """
    if not source_code.strip():
        return []
    return _splitter.split_text(source_code)
