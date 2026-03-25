"""
LLM client using Groq API for cloud inference.
Calls Groq with llama3-70b-8192 and handles response parsing.
"""
import os
import re
import json
import logging
import asyncio
from dotenv import load_dotenv
from groq import AsyncGroq, GroqError

load_dotenv()

logger = logging.getLogger(__name__)

# Enforce GROQ_API_KEY for cloud deployment
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-70b-8192"

if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY is not set. LLM features will fail in production.")

# Initialize global AsyncGroq client
groq_client = AsyncGroq(api_key=GROQ_API_KEY)


async def generate_response(prompt: str) -> str:
    """
    Core function to communicate with Groq LLM API.
    
    Args:
        prompt: Raw prompt text string.
        
    Returns:
        Generated text response from the model.
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is missing. Please configure it in the environment variables.")

    try:
        logger.info("Sending request to Groq SDK (model=%s)", GROQ_MODEL)
        
        response = await groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=GROQ_MODEL,
            temperature=0.2,
            max_tokens=2048,
        )
        
        content = response.choices[0].message.content
        logger.info("Groq response received (%d chars)", len(content))
        return content

    except GroqError as e:
        logger.error("Groq API request failed: %s", str(e))
        raise RuntimeError(f"Cloud LLM inference failed: {str(e)}")
    except Exception as e:
        logger.error("Unexpected error during Groq generation: %s", str(e))
        raise


async def analyze_debug_issue(messages: list[dict]) -> dict:
    """
    Send formatted messages to Groq and return the parsed JSON response.

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
        # Generate the raw text response via Groq
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
