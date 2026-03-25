"""
Autonomous AI Code Analysis Engine v2.
Dual-phase analysis: strict bug detection → improvement mode fallback.
Guaranteed non-empty output. Cross-file architectural analysis.
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
    "target", "bin", "obj",
}

IGNORED_EXTENSIONS = (
    ".min.js", ".min.css", ".map", ".lock", ".svg", ".png",
    ".jpg", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".gif",
    ".mp4", ".mp3", ".pdf",
)

PRIORITY_PATTERNS = [
    "route", "controller", "service", "middleware", "auth",
    "api", "handler", "model", "schema", "config", "security",
    "database", "migration", "util", "helper", "hook",
]

# ── Phase 1: Strict Bug Detection Prompt ──
STRICT_PROMPT = """You are a world-class senior software engineer performing a thorough code review.

Analyze the following code for REAL, SPECIFIC issues:
- Runtime bugs (null refs, off-by-one, race conditions)
- Security vulnerabilities (injection, XSS, auth bypass, exposed secrets)
- Performance problems (N+1 queries, memory leaks, blocking I/O)
- Critical code smells (uncaught exceptions, missing validation)

Return a JSON array. EVERY issue MUST be specific to THIS code — never generic.

Format:
[
  {{
    "issue_type": "bug | security | performance | code_smell",
    "severity": "critical | high | medium | low",
    "title": "Short, specific title",
    "description": "Explain exactly what's wrong, referencing specific variables/functions",
    "fix_suggestion": "Show the exact code change needed",
    "line_start": null,
    "line_end": null,
    "confidence_score": 0.0 to 1.0
  }}
]

Rules:
- Be specific — reference actual variable names, function names, line patterns
- No generic advice like "consider improving performance"
- If you genuinely find nothing wrong, return []

File(s): {file_path}
Language: {language}

Code:
```
{code}
```"""

# ── Phase 2: Improvement Mode Prompt (always generates results) ──
IMPROVEMENT_PROMPT = """You are a principal software architect reviewing code for quality and maintainability.

Analyze this code and provide ACTIONABLE improvements. You MUST find at least 3-5 items.

Look for:
- Missing input validation or error handling
- Hardcoded values that should be configurable
- Functions that are too long or do too many things
- Missing type hints, docstrings, or documentation
- Inconsistent naming conventions
- Missing edge case handling
- Error messages that don't help debugging
- Missing logging for important operations
- Security best practices not followed
- Scalability concerns
- Missing tests or testability issues
- Dead code or unused imports

Return a JSON array with 3-5 items minimum:
[
  {{
    "issue_type": "improvement | code_smell",
    "severity": "medium | low",
    "title": "Short, specific title",
    "description": "Explain exactly what should change and why, with code references",
    "fix_suggestion": "Show the exact improvement code",
    "line_start": null,
    "line_end": null,
    "confidence_score": 0.0 to 1.0
  }}
]

Rules:
- MUST return at least 3 items — there is ALWAYS room for improvement
- Be specific — reference actual code patterns you see
- Suggestions must be actionable, not vague

File(s): {file_path}
Language: {language}

Code:
```
{code}
```"""

# ── Phase 3: Cross-File Architecture Prompt ──
ARCHITECTURE_PROMPT = """You are a principal software architect reviewing the overall structure of a codebase.

Here is a summary of the repository:
- Repository: {repo_name}
- Languages: {languages}
- Total files: {total_files}
- Key files analyzed: {key_files}

Here are the most important code excerpts:
```
{code_excerpts}
```

Provide 2-3 system-level architectural observations:
[
  {{
    "issue_type": "improvement",
    "severity": "medium",
    "title": "Architectural observation title",
    "description": "Detailed explanation of the system-level concern",
    "fix_suggestion": "How to address this architecturally",
    "line_start": null,
    "line_end": null,
    "confidence_score": 0.6 to 0.9
  }}
]

Focus on:
- Missing error boundaries or resilience patterns
- Coupling between modules
- Missing abstraction layers
- Configuration management
- Logging and observability gaps

Return STRICT JSON array. Be specific to THIS codebase."""

BATCH_SIZE = 5
MAX_RETRIES = 3
LLM_TIMEOUT = 45  # seconds


def _should_skip_file(file_path: str) -> bool:
    """Filter out irrelevant files."""
    lower = file_path.lower()
    for ignored in IGNORED_PATHS:
        if f"/{ignored}/" in f"/{lower}/" or f"\\{ignored}\\" in f"\\{lower}\\":
            return True
    if lower.endswith(IGNORED_EXTENSIONS):
        return True
    return False


def _get_file_priority(file_path: str) -> int:
    """Score file importance (higher = analyzed first)."""
    lower = file_path.lower()
    score = 0
    for pattern in PRIORITY_PATTERNS:
        if pattern in lower:
            score += 10
    if any(ext in lower for ext in [".py", ".js", ".ts", ".jsx", ".tsx"]):
        score += 5
    if "test" in lower or "spec" in lower or "__test__" in lower:
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
    if issue.get("issue_type", "").lower() == "security" and severity in ("low", "medium"):
        severity = "high"
    return severity


async def _call_llm_with_retry(prompt: str, retries: int = MAX_RETRIES) -> str:
    """Call the LLM with retry logic and timeout protection."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            result = await asyncio.wait_for(
                generate_response(prompt),
                timeout=LLM_TIMEOUT,
            )
            logger.info("  ✓ LLM responded (%d chars) on attempt %d", len(result), attempt)
            return result
        except asyncio.TimeoutError:
            last_error = "timeout"
            logger.warning("  ⏱ LLM timeout (attempt %d/%d)", attempt, retries)
        except Exception as e:
            last_error = str(e)
            logger.warning("  ✗ LLM error (attempt %d/%d): %s", attempt, retries, str(e))
            if "RATE_LIMIT_EXCEEDED" in str(e):
                logger.error("  🚨 Groq Rate Limit Exceeded! Fast-failing analysis.")
                raise RuntimeError("RATE_LIMIT_EXCEEDED")
            
        if attempt < retries:
            await asyncio.sleep(2 ** attempt)

    raise RuntimeError(f"LLM failed after {retries} retries: {last_error}")


def _parse_llm_response(raw: str) -> list[dict]:
    """Robustly parse LLM JSON array response with logging."""
    text = raw.strip()

    # Strip markdown code fences
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            text = parts[1].strip()

    # Find outermost [ ... ]
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        json_str = text[start:end + 1]
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, list):
                logger.info("  📋 Parsed %d issues from LLM response", len(parsed))
                return parsed
        except json.JSONDecodeError as e:
            logger.warning("  ⚠ JSON parse failed: %s", str(e))
            # Log the first 200 chars of what we tried to parse
            logger.debug("  Raw JSON attempt: %s...", json_str[:200])

    # Try single object
    try:
        start_obj = text.find("{")
        end_obj = text.rfind("}")
        if start_obj != -1 and end_obj != -1:
            obj = json.loads(text[start_obj:end_obj + 1])
            if isinstance(obj, dict):
                logger.info("  📋 Parsed 1 issue (single object)")
                return [obj]
    except json.JSONDecodeError:
        pass

    logger.warning("  ❌ Could not parse any issues from LLM response")
    logger.debug("  Raw response: %s", raw[:300])
    return []


def _validate_issue(issue: dict) -> bool:
    """Validate an issue has all required fields and isn't generic."""
    if not issue.get("title") or not issue.get("description"):
        return False
    # Reject overly generic titles
    generic_titles = {"improve code", "code improvement", "general suggestion", "n/a", "none"}
    if issue["title"].lower().strip() in generic_titles:
        return False
    # Description must be at least somewhat specific
    if len(issue.get("description", "")) < 15:
        return False
    return True


async def run_analysis_pipeline(repo_id: int):
    """
    Dual-phase autonomous analysis pipeline.
    Phase 1: Strict bug detection
    Phase 2: Improvement mode (guaranteed output)
    Phase 3: Cross-file architectural analysis
    """
    db = await get_db()

    try:
        # ── Mark analyzing ──
        logger.info("=" * 60)
        logger.info("🔍 STARTING AI ANALYSIS for repo_id=%d", repo_id)
        logger.info("=" * 60)
        await db.execute(
            "UPDATE repositories SET analysis_status = 'analyzing' WHERE id = ?",
            (repo_id,)
        )
        await db.commit()

        # ── Fetch chunks with file metadata ──
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

        # ── Filter and prioritize ──
        chunks = []
        skipped = 0
        for row in rows:
            file_path = row[1]
            if _should_skip_file(file_path):
                skipped += 1
                continue
            chunks.append({
                "content": row[0],
                "file_path": file_path,
                "language": row[2] or "Unknown",
            })

        chunks.sort(key=lambda c: _get_file_priority(c["file_path"]), reverse=True)

        logger.info("📊 Stats: %d total chunks, %d filtered, %d skipped",
                     len(rows), len(chunks), skipped)

        # ── PHASE 1: Strict Bug Detection ──
        logger.info("─" * 40)
        logger.info("🔬 PHASE 1: Strict Bug Detection")
        logger.info("─" * 40)
        all_issues = []
        seen_hashes = set()
        batches_processed = 0
        rate_limit_hit = False

        for batch_start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[batch_start:batch_start + BATCH_SIZE]
            batches_processed += 1

            combined_code = ""
            file_context = set()
            for chunk in batch:
                file_context.add(chunk["file_path"])
                combined_code += f"\n// === FILE: {chunk['file_path']} ({chunk['language']}) ===\n"
                combined_code += chunk["content"] + "\n"

            file_list = ", ".join(file_context)
            logger.info("  Batch %d: analyzing %s", batches_processed, file_list)

            prompt = STRICT_PROMPT.format(
                file_path=file_list,
                language=batch[0]["language"],
                code=combined_code[:8000],
            )

            try:
                raw_response = await _call_llm_with_retry(prompt)
                issues = _parse_llm_response(raw_response)

                for issue in issues:
                    if not _validate_issue(issue):
                        continue
                    issue["severity"] = _normalize_severity(issue)
                    issue["issue_type"] = issue.get("issue_type", "code_smell").lower().strip()
                    valid_types = {"bug", "security", "performance", "code_smell", "improvement"}
                    if issue["issue_type"] not in valid_types:
                        issue["issue_type"] = "code_smell"
                    if not issue.get("file_path"):
                        issue["file_path"] = list(file_context)[0] if file_context else "unknown"
                    if not issue.get("confidence_score"):
                        issue["confidence_score"] = 0.8

                    issue_hash = _generate_issue_hash(repo_id, issue["file_path"], issue["title"], issue.get("line_start"))
                    if issue_hash in seen_hashes:
                        continue
                    seen_hashes.add(issue_hash)
                    issue["issue_hash"] = issue_hash
                    all_issues.append(issue)

            except Exception as e:
                logger.error("  ✗ Batch %d failed: %s", batches_processed, str(e))
                if "RATE_LIMIT_EXCEEDED" in str(e):
                    rate_limit_hit = True
                    break
                continue

            await asyncio.sleep(0.5)  # Rate limiting for Groq

        logger.info("🔬 Phase 1 complete: %d strict issues found in %d batches",
                     len(all_issues), batches_processed)

        # ── PHASE 2: Improvement Mode (if Phase 1 found < 3 issues) ──
        if len(all_issues) < 3 and not rate_limit_hit:
            logger.info("─" * 40)
            logger.info("💡 PHASE 2: Improvement Mode (Phase 1 found only %d issues)", len(all_issues))
            logger.info("─" * 40)

            # Take top priority files for improvement analysis
            top_files = {}
            for chunk in chunks:
                fp = chunk["file_path"]
                if fp not in top_files:
                    top_files[fp] = chunk
                if len(top_files) >= 3:
                    break

            for fp, chunk in top_files.items():
                logger.info("  Analyzing improvements for: %s", fp)
                prompt = IMPROVEMENT_PROMPT.format(
                    file_path=fp,
                    language=chunk["language"],
                    code=chunk["content"][:6000],
                )

                try:
                    raw_response = await _call_llm_with_retry(prompt)
                    issues = _parse_llm_response(raw_response)

                    for issue in issues:
                        if not _validate_issue(issue):
                            continue
                        issue["severity"] = issue.get("severity", "low").lower().strip()
                        if issue["severity"] not in {"critical", "high", "medium", "low"}:
                            issue["severity"] = "low"
                        issue["issue_type"] = issue.get("issue_type", "improvement").lower().strip()
                        if issue["issue_type"] not in {"improvement", "code_smell"}:
                            issue["issue_type"] = "improvement"
                        issue["file_path"] = fp
                        if not issue.get("confidence_score"):
                            issue["confidence_score"] = 0.7

                        issue_hash = _generate_issue_hash(repo_id, fp, issue["title"], issue.get("line_start"))
                        if issue_hash in seen_hashes:
                            continue
                        seen_hashes.add(issue_hash)
                        issue["issue_hash"] = issue_hash
                        all_issues.append(issue)

                except Exception as e:
                    logger.error("  ✗ Improvement scan failed for %s: %s", fp, str(e))
                    if "RATE_LIMIT_EXCEEDED" in str(e):
                        rate_limit_hit = True
                        break

                await asyncio.sleep(0.5)

            logger.info("💡 Phase 2 complete: total issues now %d", len(all_issues))

        # ── PHASE 3: Cross-File Architecture Analysis ──
        if not rate_limit_hit:
            logger.info("─" * 40)
        logger.info("🏗️ PHASE 3: Cross-File Architecture Analysis")
        logger.info("─" * 40)

        try:
            # Get repo info
            repo_cursor = await db.execute(
                "SELECT name, languages, total_files FROM repositories WHERE id = ?",
                (repo_id,)
            )
            repo_info = await repo_cursor.fetchone()

            # Build excerpts from top priority files
            code_excerpts = ""
            excerpt_files = []
            for chunk in chunks[:10]:  # Top 10 chunks
                if chunk["file_path"] not in excerpt_files:
                    excerpt_files.append(chunk["file_path"])
                    code_excerpts += f"\n// {chunk['file_path']}:\n"
                    code_excerpts += chunk["content"][:500] + "\n...\n"

            if repo_info and excerpt_files:
                prompt = ARCHITECTURE_PROMPT.format(
                    repo_name=repo_info[0],
                    languages=repo_info[1] or "Unknown",
                    total_files=repo_info[2] or 0,
                    key_files=", ".join(excerpt_files[:5]),
                    code_excerpts=code_excerpts[:6000],
                )

                raw_response = await _call_llm_with_retry(prompt)
                arch_issues = _parse_llm_response(raw_response)

                for issue in arch_issues:
                    if not _validate_issue(issue):
                        continue
                    issue["issue_type"] = "improvement"
                    issue["severity"] = issue.get("severity", "medium").lower().strip()
                    if issue["severity"] not in {"critical", "high", "medium", "low"}:
                        issue["severity"] = "medium"
                    issue["file_path"] = "architecture"
                    if not issue.get("confidence_score"):
                        issue["confidence_score"] = 0.7

                    issue_hash = _generate_issue_hash(repo_id, "architecture", issue["title"], None)
                    if issue_hash in seen_hashes:
                        continue
                    seen_hashes.add(issue_hash)
                    issue["issue_hash"] = issue_hash
                    all_issues.append(issue)

                logger.info("🏗️ Phase 3 complete: added %d architectural insights", len(arch_issues))

        except Exception as e:
            logger.warning("  ⚠ Architecture analysis failed: %s", str(e))
            if "RATE_LIMIT_EXCEEDED" in str(e):
                rate_limit_hit = True

        # ── Store issues in DB ──
        logger.info("─" * 40)
        logger.info("💾 Storing %d total issues", len(all_issues))
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
                    float(issue.get("confidence_score", 0.8)),
                    issue["issue_hash"],
                ))
                stored_count += 1
            except Exception as e:
                logger.warning("  ✗ Failed to store issue '%s': %s", issue.get("title", "?"), str(e))

        await db.commit()
        logger.info("💾 Stored %d issues (of %d)", stored_count, len(all_issues))

        # ── Generate summary ──
        sev_cursor = await db.execute("""
            SELECT severity, COUNT(*) FROM code_issues
            WHERE repo_id = ? AND is_false_positive = 0
            GROUP BY severity
        """, (repo_id,))
        severity_counts = dict(await sev_cursor.fetchall())

        critical = severity_counts.get("critical", 0)
        high = severity_counts.get("high", 0)
        medium = severity_counts.get("medium", 0)
        low = severity_counts.get("low", 0)
        total = critical + high + medium + low

        # Smart summary message
        if rate_limit_hit:
            summary = f"⚠️ Analysis paused: Groq AI Rate Limit Exceeded. Found {total} issues so far."
        elif critical > 0 or high > 0:
            summary = f"AI found {total} issues ({critical} critical, {high} high priority)"
        elif total > 0:
            summary = f"✅ No critical issues! Found {total} improvements to strengthen your code"
        else:
            summary = "✅ Code looks clean — no significant issues detected"

        await db.execute(
            "UPDATE repositories SET analysis_status = 'analyzed', summary_message = ? WHERE id = ?",
            (summary, repo_id)
        )
        await db.commit()

        logger.info("=" * 60)
        logger.info("✅ ANALYSIS COMPLETE for repo_id=%d", repo_id)
        logger.info("   %s", summary)
        logger.info("=" * 60)

    except Exception as e:
        logger.error("❌ ANALYSIS PIPELINE FAILED for repo_id=%d: %s", repo_id, str(e))
        await db.execute(
            "UPDATE repositories SET analysis_status = 'failed', summary_message = ? WHERE id = ?",
            (f"Analysis failed: {str(e)}", repo_id)
        )
        await db.commit()
    finally:
        await db.close()
