"""
Autonomous AI Code Analysis Engine.
Triggered automatically after indexing completes.
Scans all code chunks via Groq LLM with batching, deduplication, retry, and severity normalization.
"""
import hashlib
import json
import logging
import asyncio
from typing import Optional

from app.database.db import get_db
from app.rag.llm_client import generate_response

logger = logging.getLogger(__name__)

# ── File filtering ──
IGNORED_PATHS = {
    "node_modules", "dist", "build", ".next", "__pycache__",
    ".git", "venv", ".venv", "coverage", ".cache", "vendor",
    "target", "bin", "obj", ".min.", "bundle.", "chunk.",
}

PRIORITY_PATTERNS = [
    "route", "controller", "service", "middleware", "auth",
    "api", "handler", "model", "schema", "config", "security",
    "database", "migration", "util", "helper", "hook",
]

# ── Analysis Prompt ──
ANALYSIS_PROMPT = """You are a senior software engineer and security analyst.

Analyze the following code and identify:
- Bugs
- Security vulnerabilities
- Performance issues
- Code smells
- Improvements

Return STRICT JSON array:
[
  {{
    "issue_type": "bug | security | performance | code_smell | improvement",
    "severity": "critical | high | medium | low",
    "title": "short title",
    "description": "clear explanation",
    "fix_suggestion": "exact fix",
    "line_start": null,
    "line_end": null
  }}
]

Rules:
- No hallucinations
- No generic advice
- Only real, specific issues
- Return [] if no issues found

File: {file_path}
Language: {language}

Code:
```
{code}
```"""

BATCH_SIZE = 5
MAX_RETRIES = 3
LLM_TIMEOUT = 30  # seconds


def _should_skip_file(file_path: str) -> bool:
    """Filter out irrelevant files (vendor, build artifacts, minified)."""
    lower = file_path.lower()
    for ignored in IGNORED_PATHS:
        if ignored in lower:
            return True
    if lower.endswith((".min.js", ".min.css", ".map", ".lock", ".svg", ".png", ".jpg", ".ico")):
        return True
    return False


def _get_file_priority(file_path: str) -> int:
    """Score file importance (higher = more important, analyzed first)."""
    lower = file_path.lower()
    score = 0
    for pattern in PRIORITY_PATTERNS:
        if pattern in lower:
            score += 10
    # Backend logic files are highest priority
    if any(ext in lower for ext in [".py", ".js", ".ts"]):
        score += 5
    # Test files are lower priority
    if "test" in lower or "spec" in lower:
        score -= 5
    return score


def _generate_issue_hash(repo_id: int, file_path: str, title: str, line_start: Optional[int]) -> str:
    """Create a deterministic hash for deduplication."""
    raw = f"{repo_id}:{file_path}:{title}:{line_start or 0}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _normalize_severity(issue: dict) -> str:
    """Force security issues to high/critical. Standardize all severities."""
    severity = issue.get("severity", "medium").lower().strip()
    valid = {"critical", "high", "medium", "low"}
    if severity not in valid:
        severity = "medium"

    # Security issues should never be low
    if issue.get("issue_type", "").lower() == "security" and severity in ("low", "medium"):
        severity = "high"

    return severity


async def _call_llm_with_retry(prompt: str, retries: int = MAX_RETRIES) -> str:
    """Call the LLM with retry logic and timeout protection."""
    for attempt in range(1, retries + 1):
        try:
            result = await asyncio.wait_for(
                generate_response(prompt),
                timeout=LLM_TIMEOUT,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning("LLM call timed out (attempt %d/%d)", attempt, retries)
        except Exception as e:
            logger.warning("LLM call failed (attempt %d/%d): %s", attempt, retries, str(e))
        if attempt < retries:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff

    raise RuntimeError("LLM call failed after all retries")


def _parse_llm_response(raw: str) -> list[dict]:
    """Robustly parse LLM JSON array response."""
    text = raw.strip()

    # Strip markdown code fences
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    # Find outermost [ ... ]
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        text = text[start:end + 1]

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    # If it returned a single object instead of array
    try:
        start_obj = text.find("{")
        end_obj = text.rfind("}")
        if start_obj != -1 and end_obj != -1:
            obj = json.loads(text[start_obj:end_obj + 1])
            if isinstance(obj, dict):
                return [obj]
    except json.JSONDecodeError:
        pass

    return []


async def run_analysis_pipeline(repo_id: int):
    """
    Main autonomous analysis pipeline.
    Fetches all indexed code chunks, sends them to the LLM in batches,
    deduplicates and stores issues in the database.
    """
    db = await get_db()

    try:
        # ── Step 1: Mark repo as analyzing ──
        logger.info("🔍 Starting AI analysis for repo_id=%d", repo_id)
        await db.execute(
            "UPDATE repositories SET analysis_status = 'analyzing' WHERE id = ?",
            (repo_id,)
        )
        await db.commit()

        # ── Step 2: Fetch all chunks with file metadata ──
        cursor = await db.execute("""
            SELECT cc.content, fm.file_path, fm.language
            FROM code_chunks cc
            JOIN file_metadata fm ON cc.file_id = fm.id
            WHERE cc.repo_id = ?
            ORDER BY fm.file_path, cc.chunk_index
        """, (repo_id,))
        rows = await cursor.fetchall()

        if not rows:
            logger.warning("No code chunks found for repo_id=%d", repo_id)
            await db.execute(
                "UPDATE repositories SET analysis_status = 'analyzed', summary_message = 'No code to analyze' WHERE id = ?",
                (repo_id,)
            )
            await db.commit()
            return

        # ── Step 3: Filter and prioritize ──
        chunks = []
        for row in rows:
            file_path = row[1]
            if _should_skip_file(file_path):
                continue
            chunks.append({
                "content": row[0],
                "file_path": file_path,
                "language": row[2] or "Unknown",
            })

        # Sort by priority (important files first)
        chunks.sort(key=lambda c: _get_file_priority(c["file_path"]), reverse=True)

        logger.info("Analyzing %d chunks (filtered from %d total) for repo_id=%d",
                     len(chunks), len(rows), repo_id)

        # ── Step 4: Batch and analyze ──
        all_issues = []
        seen_hashes = set()

        for batch_start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[batch_start:batch_start + BATCH_SIZE]

            # Combine batch into a single prompt
            combined_code = ""
            file_context = set()
            for chunk in batch:
                file_context.add(chunk["file_path"])
                combined_code += f"\n// === FILE: {chunk['file_path']} ({chunk['language']}) ===\n"
                combined_code += chunk["content"] + "\n"

            prompt = ANALYSIS_PROMPT.format(
                file_path=", ".join(file_context),
                language=batch[0]["language"],
                code=combined_code[:8000],  # Cap at 8K chars to stay within context
            )

            try:
                raw_response = await _call_llm_with_retry(prompt)
                issues = _parse_llm_response(raw_response)

                for issue in issues:
                    # Validate required fields
                    if not issue.get("title") or not issue.get("description"):
                        continue

                    # Normalize
                    issue["severity"] = _normalize_severity(issue)
                    issue["issue_type"] = issue.get("issue_type", "improvement").lower().strip()
                    valid_types = {"bug", "security", "performance", "code_smell", "improvement"}
                    if issue["issue_type"] not in valid_types:
                        issue["issue_type"] = "improvement"

                    # Assign file_path if not set
                    if not issue.get("file_path"):
                        issue["file_path"] = list(file_context)[0] if file_context else "unknown"

                    # Deduplication
                    issue_hash = _generate_issue_hash(
                        repo_id,
                        issue["file_path"],
                        issue["title"],
                        issue.get("line_start"),
                    )
                    if issue_hash in seen_hashes:
                        continue
                    seen_hashes.add(issue_hash)

                    issue["issue_hash"] = issue_hash
                    all_issues.append(issue)

            except Exception as e:
                logger.error("Batch analysis failed for files %s: %s", list(file_context), str(e))
                continue

            # Yield control between batches
            await asyncio.sleep(0.1)

        # ── Step 5: Store issues in DB ──
        stored_count = 0
        for issue in all_issues:
            try:
                await db.execute("""
                    INSERT OR IGNORE INTO code_issues
                    (repo_id, file_path, issue_type, severity, title, description,
                     fix_suggestion, line_start, line_end, confidence_score, issue_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    repo_id,
                    issue["file_path"],
                    issue["issue_type"],
                    issue["severity"],
                    issue["title"],
                    issue["description"],
                    issue.get("fix_suggestion", ""),
                    issue.get("line_start"),
                    issue.get("line_end"),
                    issue.get("confidence_score", 0.8),
                    issue["issue_hash"],
                ))
                stored_count += 1
            except Exception as e:
                logger.warning("Failed to store issue: %s", str(e))

        await db.commit()

        # ── Step 6: Generate summary ──
        severity_cursor = await db.execute("""
            SELECT severity, COUNT(*) FROM code_issues
            WHERE repo_id = ? AND is_false_positive = 0
            GROUP BY severity
        """, (repo_id,))
        severity_counts = dict(await severity_cursor.fetchall())

        critical = severity_counts.get("critical", 0)
        high = severity_counts.get("high", 0)
        medium = severity_counts.get("medium", 0)
        low = severity_counts.get("low", 0)
        total = critical + high + medium + low

        summary = f"AI found {total} issues"
        if critical > 0:
            summary += f" ({critical} critical"
            if high > 0:
                summary += f", {high} high"
            summary += ")"
        elif high > 0:
            summary += f" ({high} high priority)"

        await db.execute(
            "UPDATE repositories SET analysis_status = 'analyzed', summary_message = ? WHERE id = ?",
            (summary, repo_id)
        )
        await db.commit()

        logger.info("✅ Analysis complete for repo_id=%d: %s", repo_id, summary)

    except Exception as e:
        logger.error("❌ Analysis pipeline FAILED for repo_id=%d: %s", repo_id, str(e))
        await db.execute(
            "UPDATE repositories SET analysis_status = 'failed', summary_message = ? WHERE id = ?",
            (f"Analysis failed: {str(e)}", repo_id)
        )
        await db.commit()
    finally:
        await db.close()
