"""
LLM client with dual provider support:
  - Groq (cloud): Uses Groq SDK with llama-3.3-70b-versatile
  - Ollama (local): Uses HTTP calls to localhost:11434

Provider is selected via LLM_PROVIDER environment variable.
"""
import os
import re
import json
import logging
import asyncio
import httpx
from app.config import GROQ_API_KEY, LLM_PROVIDER, OLLAMA_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Groq Cloud Provider
# ─────────────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"
_groq_client = None


def _get_groq_client():
    """Lazy-initialize the Groq client."""
    global _groq_client
    current_key = os.getenv("GROQ_API_KEY") or GROQ_API_KEY
    if not current_key:
        raise ValueError("GROQ_API_KEY is missing. Please configure it in environment variables.")
    if _groq_client is None or _groq_client.api_key != current_key:
        from groq import AsyncGroq
        _groq_client = AsyncGroq(api_key=current_key, max_retries=3)
    return _groq_client


async def _generate_groq(prompt: str) -> str:
    """Generate response using Groq Cloud API."""
    from groq import GroqError
    client = _get_groq_client()
    try:
        logger.info("Sending request to Groq SDK (model=%s)", GROQ_MODEL)
        response = await client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=GROQ_MODEL,
            temperature=0.2,
            max_tokens=4096,
        )
        content = response.choices[0].message.content
        logger.info("Groq response received (%d chars)", len(content))
        return content
    except GroqError as e:
        logger.error("Groq API request failed: %s", str(e))
        raise RuntimeError(f"Cloud LLM inference failed: {str(e)}")


# ─────────────────────────────────────────────
# Ollama Local Provider
# ─────────────────────────────────────────────

async def _check_ollama_health() -> bool:
    """Check if Ollama is running at the configured URL."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(OLLAMA_URL)
            return r.status_code == 200
    except Exception:
        return False


async def _generate_ollama(prompt: str) -> str:
    """Generate response using local Ollama instance."""
    is_alive = await _check_ollama_health()
    if not is_alive:
        raise ConnectionError(
            f"Ollama is not running at {OLLAMA_URL}. "
            "Start Ollama with 'ollama serve' and try again."
        )

    url = f"{OLLAMA_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 4096,
        },
    }

    logger.info("Sending request to Ollama (model=%s, url=%s)", OLLAMA_MODEL, OLLAMA_URL)
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)

        if response.status_code != 200:
            error_detail = response.text[:300]
            logger.error("Ollama returned HTTP %d: %s", response.status_code, error_detail)
            raise RuntimeError(f"Ollama error (HTTP {response.status_code}): {error_detail}")

        data = response.json()
        content = data.get("response", "")
        if not content:
            raise RuntimeError("Ollama returned empty response")

        logger.info("Ollama response received (%d chars)", len(content))
        return content

    except httpx.ConnectError:
        raise ConnectionError(f"Cannot connect to Ollama at {OLLAMA_URL}")
    except httpx.TimeoutException:
        raise RuntimeError("Ollama request timed out (120s)")


# ─────────────────────────────────────────────
# Public API — auto-dispatches to the right provider
# ─────────────────────────────────────────────

async def generate_response(prompt: str) -> str:
    """
    Core function to communicate with the configured LLM provider.

    Uses LLM_PROVIDER env var to select:
      - "ollama" → local Ollama instance
      - "groq"   → Groq Cloud API (default)

    Args:
        prompt: Raw prompt text string.
    Returns:
        Generated text response from the model.
    """
    provider = os.getenv("LLM_PROVIDER", LLM_PROVIDER).lower()

    if provider == "ollama":
        return await _generate_ollama(prompt)
    else:
        return await _generate_groq(prompt)


async def analyze_debug_issue(messages: list[dict]) -> dict:
    """
    Send formatted messages to LLM and return the parsed JSON response.

    Args:
        messages: Chat-format messages from prompt_builder

    Returns:
        Parsed dict with root_cause, explanation, suggested_fix, etc.
    """
    # Convert prompt builder messages to a single strong prompt for the prompt arg
    prompt_parts = []
    for msg in messages:
        role = msg["role"].upper()
        content = msg["content"]
        prompt_parts.append(f"### {role}\n{content}\n")

    full_prompt = "\n".join(prompt_parts) + "\n### RESPONSE (JSON ONLY)\n"

    try:
        # Generate the raw text response via configured provider
        content = await generate_response(full_prompt)

    except Exception as e:
        raise RuntimeError(f"Analysis failed: {str(e)}")

    # ── Robust JSON extraction ──
    json_str = content.strip()

    # Strip markdown code fences
    if "```json" in content:
        json_str = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        json_str = content.split("```")[1].split("```")[0].strip()

    # Extract the outermost { ... } if present
    start = json_str.find("{")
    end = json_str.rfind("}")
    if start != -1 and end != -1:
        json_str = json_str[start:end + 1]

    # Fix unescaped backslashes (e.g. server\controllers\app.js)
    json_str = re.sub(
        r'\\(?!["\\/bfnrtu])',
        r'/',
        json_str,
    )

    result = None

    # Attempt 1: Direct JSON parse
    try:
        result = json.loads(json_str)
        logger.info("LLM response parsed via direct JSON")
    except json.JSONDecodeError:
        pass

    # Attempt 2: Try to extract JSON object with regex
    if result is None:
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content)
        if match:
            try:
                cleaned = re.sub(r'\\(?!["\\/bfnrtu])', '/', match.group())
                result = json.loads(cleaned)
                logger.info("LLM response parsed via regex extraction")
            except json.JSONDecodeError:
                pass

    # Attempt 3: Extract fields with regex from raw text
    if result is None:
        logger.warning("Falling back to regex field extraction for LLM response")

        def extract(field):
            pattern = rf'"{field}"\s*:\s*"((?:[^"\\]|\\.)*)"|{field}[:\s]+(.*?)(?:\n|$)'
            m = re.search(pattern, content, re.IGNORECASE)
            return m.group(1) or m.group(2) if m else ""

        result = {
            "root_cause": extract("root_cause") or content[:200],
            "explanation": extract("explanation") or content,
            "suggested_fix": extract("suggested_fix") or "Review the AI output manually",
            "code_patch": extract("code_patch") or "",
            "related_files": [],
            "severity": extract("severity") or "medium",
            "category": extract("category") or "ERROR",
        }

        # Try to extract related_files array
        files_match = re.search(r'"related_files"\s*:\s*\[(.*?)\]', content)
        if files_match:
            result["related_files"] = [
                f.strip().strip('"').strip("'")
                for f in files_match.group(1).split(",")
                if f.strip()
            ]

    # Ensure all expected fields exist
    defaults = {
        "root_cause": "Analysis not available",
        "explanation": "The model failed to provide a detailed explanation.",
        "suggested_fix": "No fix suggested.",
        "code_patch": "",
        "related_files": [],
        "severity": "medium",
        "category": "Unknown",
    }
    for key, default in defaults.items():
        if key not in result or not result[key]:
            result[key] = default

    return result
