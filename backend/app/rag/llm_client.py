"""
LLM client using Ollama for local inference.
Calls Ollama's /api/generate endpoint and handles response parsing.
"""
import os
import re
import json
import logging
import requests
import asyncio
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")


async def analyze_debug_issue(messages: list[dict]) -> dict:
    """
    Send a prompt to Ollama and return the parsed JSON response.

    Args:
        messages: Chat-format messages from prompt_builder

    Returns:
        Parsed dict with root_cause, explanation, suggested_fix, etc.
    """
    # Ollama /api/generate expects a single prompt string, or we can use /api/chat.
    # The requirement specifically mentioned /api/generate with "prompt" field.
    # Let's convert the messages list to a single prompt string for /api/generate.
    
    prompt_parts = []
    for msg in messages:
        role = msg["role"].upper()
        content = msg["content"]
        prompt_parts.append(f"### {role}\n{content}\n")
    
    full_prompt = "\n".join(prompt_parts) + "\n### RESPONSE (JSON ONLY)\n"

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.3
        }
    }

    logger.info("Sending LLM request to %s (model=%s)", OLLAMA_URL, OLLAMA_MODEL)

    try:
        # Run synchronous request in executor to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                timeout=180
            )
        )
        
        if response.status_code != 200:
            logger.error("Ollama returned status %d: %s", response.status_code, response.text[:200])
            raise ValueError(f"Ollama error: {response.text}")
            
        data = response.json()
        content = data.get("response", "").strip()
        logger.info("LLM response received (%d chars)", len(content))
        
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama at %s", OLLAMA_URL)
        raise ConnectionError("Local LLM service unavailable. Start Ollama.")
    except Exception as e:
        logger.error("Ollama request failed: %s", e)
        raise RuntimeError(f"Ollama analysis failed: {str(e)}")

    # ── Robust JSON extraction ──
    json_str = content

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
    # Replace single backslashes that aren't valid JSON escapes
    json_str = re.sub(
        r'\\(?!["\\/bfnrtu])',   # backslash NOT followed by valid JSON escape char
        r'/',                     # replace with forward slash
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
