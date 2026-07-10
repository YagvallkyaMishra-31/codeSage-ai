"""
RAG Chatbot API routes.
Provides a conversational interface for asking questions about indexed codebases.
Uses semantic search to retrieve relevant code context and Groq LLM for generation.
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.search_service import semantic_search
from app.rag.llm_client import generate_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["RAG Chatbot"])

# Minimum relevance score to include a source (filters noise)
MIN_RELEVANCE_SCORE = 0.25


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    repo_id: Optional[int] = None
    history: list[ChatMessage] = []


RAG_SYSTEM_PROMPT = """You are CodeSage AI, an expert software engineer and code assistant. You have access to the user's indexed repository code via RAG retrieval.

BEHAVIOR:
- For greetings or casual messages (hi, hello, hey, thanks, etc.), respond naturally and briefly. Do NOT reference code context for casual messages.
- For code-related questions, analyze the retrieved code context thoroughly and provide specific, actionable answers.
- When referencing code, always mention the file path and quote the relevant snippet.
- Use markdown formatting: **bold** for emphasis, `inline code`, and ```code blocks``` with language tags.
- Be concise but thorough. Don't pad responses with filler.
- If the code context doesn't contain enough information to answer, say so honestly and suggest what the user could try instead.
- For debugging questions, explain the root cause clearly, then provide a fix with code.
- For "how does X work" questions, trace through the code and explain the data flow.
"""


def _is_casual_message(msg: str) -> bool:
    """Check if a message is casual (greeting, thanks, etc.) vs a code question."""
    casual_keywords = {
        "hi", "hii", "hello", "hey", "yo", "sup", "thanks", "thank you",
        "ok", "okay", "cool", "nice", "great", "awesome", "bye", "goodbye",
        "good morning", "good evening", "good night", "gm", "gn",
    }
    cleaned = msg.strip().lower().rstrip("!?.,:;")
    return cleaned in casual_keywords or len(cleaned) < 4


@router.post("/ask")
async def chat_ask(request: ChatRequest):
    """
    RAG-powered chat endpoint.
    1. Checks if message is casual (skip RAG) or code-related (use RAG)
    2. Retrieves relevant code from FAISS vector store (if code question)
    3. Builds a prompt with code context + chat history
    4. Calls Groq LLM for a grounded response
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    logger.info("Chat request: msg='%s', repo_id=%s, history_len=%d",
                request.message[:80], request.repo_id, len(request.history))

    is_casual = _is_casual_message(request.message)

    # Step 1: Semantic search (skip for casual messages)
    retrieved_chunks = []
    if not is_casual:
        retrieved_chunks = await semantic_search(
            query=request.message,
            top_k=5,
            repo_id=request.repo_id,
        )
        # Filter out low-relevance results
        retrieved_chunks = [c for c in retrieved_chunks if c.get("score", 0) >= MIN_RELEVANCE_SCORE]
        logger.info("Retrieved %d relevant code chunks (after filtering)", len(retrieved_chunks))

    # Step 2: Format code context
    if retrieved_chunks:
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            context_parts.append(
                f"--- [{i}] {chunk['file_path']} ({chunk.get('language', 'Unknown')}) "
                f"[relevance: {chunk.get('score', 0):.2f}] ---\n"
                f"{chunk.get('chunk', chunk.get('chunk_text', ''))}"
            )
        code_context = "\n\n".join(context_parts)
    else:
        code_context = None

    # Step 3: Build conversation prompt
    prompt_parts = [f"### SYSTEM\n{RAG_SYSTEM_PROMPT}"]

    # Add code context only if we have relevant results
    if code_context:
        prompt_parts.append(f"### RETRIEVED CODE CONTEXT\n{code_context}")

    # Add chat history (last 6 messages max to stay within context window)
    for msg in request.history[-6:]:
        role = msg.role.upper()
        prompt_parts.append(f"### {role}\n{msg.content}")

    # Add current user message
    prompt_parts.append(f"### USER\n{request.message}")
    prompt_parts.append("### ASSISTANT")

    full_prompt = "\n\n".join(prompt_parts)

    # Step 4: Call LLM
    try:
        response = await generate_response(full_prompt)
    except Exception as e:
        logger.error("Chat LLM call failed: %s", str(e))
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")

    # Step 5: Return response with filtered sources (only for code questions)
    sources = []
    if not is_casual and retrieved_chunks:
        sources = [
            {
                "file_path": c.get("file_path", "unknown"),
                "language": c.get("language", "Unknown"),
                "score": round(c.get("score", 0), 3),
                "snippet": (c.get("chunk", c.get("chunk_text", "")))[:200] + "..."
                if len(c.get("chunk", c.get("chunk_text", ""))) > 200
                else c.get("chunk", c.get("chunk_text", "")),
            }
            for c in retrieved_chunks
        ]

    return {
        "reply": response,
        "sources": sources,
        "repo_id": request.repo_id,
    }
