"""
Autonomous AI Code Analysis Engine v3.
Three-phase analysis: strict bug detection → improvement mode → cross-file architecture.
Guaranteed non-empty output with fallback generation.
Confidence scoring, raw LLM logging, and enhanced debugging support.
"""
import hashlib
import json
import logging
import asyncio
import re
from typing import Optional

from app.database.db import get_db
from app.rag.llm_client import generate_response

logger = logging.getLogger(__name__)

# ── File filtering ──
IGNORED_PATHS = {
    "node_modules", "dist", "build", ".next", "__pycache__",
    ".git", "venv", ".venv", "coverage", ".cache", "vendor",
    "target", "bin", "obj", ".idea", ".vscode",
}

IGNORED_EXTENSIONS = (
    ".min.js", ".min.css", ".map", ".lock", ".svg", ".png",
    ".jpg", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".gif",
    ".mp4", ".mp3", ".pdf", ".env", ".md", ".txt", ".log",
)

PRIORITY_PATTERNS = [
    "route", "controller", "service", "middleware", "auth",
    "api", "handler", "model", "schema", "config", "security",
    "database", "migration", "util", "helper", "hook",
    "index", "app", "server", "main",
]

# ── Phase 1: Strict Bug Detection Prompt ──
STRICT_PROMPT = """You are a world-class senior software engineer and security auditor performing a deep code review.

TASK: Analyze the following code and find REAL, SPECIFIC issues. Think step by step:
1. Read through each function and trace the logic
2. Check every variable for potential null/undefined access
3. Check every external input for missing validation
4. Check every async operation for missing error handling
5. Check for security issues (injection, XSS, auth bypass, hardcoded secrets)
6. Check for performance anti-patterns (N+1 queries, unnecessary loops, memory leaks)

You MUST find at least 1-2 genuine issues. Every non-trivial code file has something wrong or suboptimal.

Return a JSON array. EVERY issue MUST reference specific code from this file:

[
  {{
    "issue_type": "bug | security | performance | code_smell",
    "severity": "critical | high | medium | low",
    "title": "Short, specific title mentioning the actual function/variable",
    "description": "Explain exactly what's wrong. Reference the specific function name, variable name, or code pattern.",
    "impact": "What can go wrong technically (e.g. 'Database corruption', 'Authentication bypass')",
    "why_it_matters": "Real-world consequence of this failure (e.g. 'Users can access other users data', 'Server crashes under load')",
    "fix_suggestion": "Show the exact replacement code or describe the precise change needed using actual code symbols",
    "file_path": "{file_path}",
    "line_start": null,
    "line_end": null,
    "confidence_score": 0.0
  }}
]

CONFIDENCE SCORING:
- 0.9-1.0: Definite bug, will cause runtime error
- 0.7-0.89: Very likely issue, needs attention
- 0.5-0.69: Probable issue, should investigate

STRICT RULES:
- Reference actual variable names, function names, and code patterns from THIS code
- NO generic advice like "consider improving performance"
- Each title must contain a specific identifier from the code (function/variable/class name)
- Each description must explain WHAT goes wrong and WHEN
- The fix_suggestion MUST reference actual code symbols and suggest precise changes.
- If you genuinely find nothing critical, find at least code smells or missing validation
- Return ONLY the JSON array, no other text

File(s): {file_path}
Language: {language}

Code (with line numbers for reference):
```
{code}
```"""

# ── Phase 2: Improvement Mode Prompt (mandatory output) ──
IMPROVEMENT_PROMPT = """You are a principal software architect reviewing production code for quality improvements.

TASK: Find AT LEAST 3-5 actionable improvements in this code. There is ALWAYS room for improvement.

Check systematically for:
1. MISSING VALIDATION: Are function inputs validated? Are return values checked?
2. ERROR HANDLING: Are there try/catch blocks? Do they catch specific errors? Are errors logged?
3. HARDCODED VALUES: Are there magic numbers, hardcoded URLs, API keys, or config values?
4. FUNCTION COMPLEXITY: Are functions doing too many things? Are they longer than 30 lines?
5. NAMING: Are variables descriptive? Are conventions consistent?
6. TYPE SAFETY: Are there missing type hints/annotations? Are types correct?
7. SECURITY: Is user input sanitized? Are secrets exposed? Is there proper auth checking?
8. SCALABILITY: Will this code work with 10x data? Are there O(n²) operations?
9. DRY VIOLATIONS: Is code duplicated? Could shared utilities be extracted?
10. MISSING LOGGING: Are important operations logged? Are errors traceable?
11. DEAD CODE: Are there unused imports, unreachable branches, commented-out code?
12. EDGE CASES: What happens with empty arrays, null values, zero-length strings?

Return a JSON array with EXACTLY 3-5 items:
[
  {{
    "issue_type": "improvement | code_smell",
    "severity": "medium | low",
    "title": "Short title mentioning the specific function/variable/pattern",
    "description": "Explain exactly what should change and why. Reference the specific code pattern you see.",
    "impact": "What technical problem does this code smell cause?",
    "why_it_matters": "Real-world consequence or risk of ignoring this improvement",
    "fix_suggestion": "Show the exact improved code or describe the precise change referencing actual code variables/functions.",
    "file_path": "{file_path}",
    "line_start": null,
    "line_end": null,
    "confidence_score": 0.7
  }}
]

MANDATORY RULES:
- You MUST return EXACTLY 3-5 items — there is ALWAYS room for improvement
- Every title MUST contain a specific identifier from the code
- Every description MUST reference actual code patterns you see in the file
- Suggestions must be ACTIONABLE — show the exact code change
- DO NOT return generic advice like "add more tests" without referencing specific untested paths
- Return ONLY the JSON array, no other text

File: {file_path}
Language: {language}

Code (with line numbers):
```
{code}
```"""

# ── Phase 3: Cross-File Architecture Prompt ──
ARCHITECTURE_PROMPT = """You are a principal software architect reviewing the overall structure of a codebase.

Repository: {repo_name}
Languages: {languages}
Total files: {total_files}

Here are the functional summaries of the most critical files in the codebase:
```
{file_summaries}
```

Provide EXACTLY 2-3 system-level architectural observations about this SPECIFIC codebase.

Consider:
1. ERROR PROPAGATION: How do errors flow between modules? Are they handled consistently?
2. DEPENDENCY COUPLING: Are modules tightly coupled? Could they be more independent?
3. CONFIGURATION: Are settings hardcoded or properly externalized?
4. API DESIGN: Are endpoints consistent? Do they follow REST conventions?
5. DATA FLOW: Is data validation done at boundaries? Is there a clear data flow?
6. OBSERVABILITY: Is there consistent logging? Can you trace a request through the system?
7. RESILIENCE: What happens when external services fail? Are there retries/circuit breakers?
8. SEPARATION OF CONCERNS: Are business logic, data access, and presentation properly separated?

Return a JSON array:
[
  {{
    "issue_type": "improvement",
    "severity": "medium | high",
    "title": "Architectural observation title referencing specific modules/patterns",
    "description": "Detailed explanation referencing specific files and functional summaries you observed",
    "impact": "What system-wide failure, vulnerability, or bottleneck does this cause?",
    "why_it_matters": "Real-world operational, security, or maintainability consequence",
    "fix_suggestion": "Concrete architectural recommendation with implementation guidance",
    "file_path": "architecture",
    "line_start": null,
    "line_end": null,
    "confidence_score": 0.7
  }}
]

RULES:
- Be specific to THIS codebase — reference actual file names and cross-file dependencies from the summaries
- Each observation must uncover a system-level issue (e.g. broken flows, API-to-model mismatches, auth gaps)
- Return ONLY the JSON array, no other text"""

# ── File Summarization Prompt ──
SUMMARIZATION_PROMPT = """You are an expert system architect analyzing a codebase file.

TASK: Extract the core purpose and structural dependencies of this code to be used for cross-file reasoning later.

Generate a concise summary in this JSON format:
{{
  "purpose": "1-2 sentences on what this file fundamentally does",
  "key_functions": ["func1: does X", "func2: handles Y"],
  "dependencies": ["moduleA", "database", "third-party lib"]
}}

Return ONLY the JSON object, no markdown, no other text.

File: {file_path}
Language: {language}
Code:
```
{code}
```"""

BATCH_SIZE = 3  # Smaller batches for more focused analysis
MAX_RETRIES = 3
LLM_TIMEOUT = 60  # Increased timeout for complex analysis


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


def _add_line_numbers(code: str) -> str:
    """Add line numbers to code for better LLM context."""
    lines = code.split("\n")
    numbered = []
    for i, line in enumerate(lines, 1):
        numbered.append(f"{i:4d} | {line}")
    return "\n".join(numbered)


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
            # Raw response logging for debugging
            logger.debug("  📝 Raw LLM response (first 500 chars): %s", result[:500])
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
            wait_time = 2 ** attempt
            logger.info("  ⏳ Waiting %ds before retry...", wait_time)
            await asyncio.sleep(wait_time)

    raise RuntimeError(f"LLM failed after {retries} retries: {last_error}")


def _parse_llm_response(raw: str) -> list[dict]:
    """Robustly parse LLM JSON array response with comprehensive logging."""
    text = raw.strip()

    # Log what we're trying to parse
    logger.info("  🔍 Attempting to parse LLM response (%d chars)", len(text))

    # Strip markdown code fences
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            text = parts[1].strip()
            # Remove language identifier if present (e.g., "javascript\n[...")
            if text and not text.startswith("[") and not text.startswith("{"):
                newline_idx = text.find("\n")
                if newline_idx != -1:
                    text = text[newline_idx + 1:].strip()

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
            logger.warning("  ⚠ JSON parse failed (array): %s", str(e))
            logger.debug("  Raw JSON attempt: %s...", json_str[:300])

            # Try to fix common JSON issues
            try:
                # Fix trailing commas
                fixed = re.sub(r',\s*]', ']', json_str)
                fixed = re.sub(r',\s*}', '}', fixed)
                parsed = json.loads(fixed)
                if isinstance(parsed, list):
                    logger.info("  📋 Parsed %d issues after JSON fix", len(parsed))
                    return parsed
            except json.JSONDecodeError:
                pass

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
    logger.info("  📝 Unparseable response (first 400 chars): %s", raw[:400])
    return []


def _calculate_priority_score(issue: dict) -> float:
    """Calculate the priority score based on severity, confidence, and impact."""
    severity_weight = {
        "critical": 4.0,
        "high": 3.0,
        "medium": 2.0,
        "low": 1.0
    }.get(issue.get("severity", "medium").lower(), 2.0)
    
    impact_score = 0.4  # Default Code Quality
    issue_type = issue.get("issue_type", "").lower()
    
    if issue_type == "security":
        impact_score = 1.0
    elif issue_type == "bug" or "data" in issue.get("impact", "").lower():
        impact_score = 0.8
    elif issue_type == "performance":
        impact_score = 0.6
        
    # The impact text itself can also elevate score if it mentions auth
    impact_text = issue.get("impact", "").lower() + " " + issue.get("why_it_matters", "").lower()
    if "auth" in impact_text or "security" in impact_text or "bypass" in impact_text:
        impact_score = max(impact_score, 1.0)
        
    confidence_score = float(issue.get("confidence_score", 0.8))
    
    # Priority Formula: (severity * 0.5) + (confidence * 0.3) + (impact * 0.2)
    score = (severity_weight * 0.5) + (confidence_score * 0.3) + (impact_score * 0.2)
    return round(score, 2)


def _validate_issue(issue: dict) -> bool:
    """Validate an issue has all required fields and isn't generic."""
    if not issue.get("title") or not issue.get("description"):
        return False
    # Reject overly generic titles
    generic_titles = {
        "improve code", "code improvement", "general suggestion",
        "n/a", "none", "no issues", "not applicable",
    }
    if issue["title"].lower().strip() in generic_titles:
        return False
    # Description must be at least somewhat specific
    if len(issue.get("description", "")) < 20:
        return False
        
    # Apply default impact if missing, though prompts now mandate it
    if not issue.get("impact"):
        issue["impact"] = "General code quality issue"
    if not issue.get("why_it_matters"):
        issue["why_it_matters"] = "May affect maintainability or edge-case stability"
        
    issue["priority_score"] = _calculate_priority_score(issue)
    return True


def _generate_fallback_improvements(chunks: list[dict], repo_id: int) -> list[dict]:
    """
    Generate deterministic fallback improvements by scanning code for common patterns.
    This ensures GUARANTEED non-empty output even if all LLM calls fail.
    """
    logger.info("  🔄 Generating fallback improvements from code patterns...")
    fallbacks = []

    for chunk in chunks[:5]:  # Check top 5 priority files
        code = chunk["content"]
        fp = chunk["file_path"]
        lang = chunk["language"]

        # Check for missing error handling
        if lang in ("JavaScript", "TypeScript"):
            if ".then(" in code and ".catch(" not in code:
                fallbacks.append({
                    "issue_type": "improvement",
                    "severity": "medium",
                    "title": f"Missing .catch() on Promise chain in {fp.split('/')[-1]}",
                    "description": f"File '{fp}' contains .then() Promise chains without corresponding .catch() handlers. Unhandled Promise rejections will crash Node.js processes in production and make debugging extremely difficult.",
                    "fix_suggestion": "Add .catch(err => { console.error('Operation failed:', err); }) to every Promise chain, or use async/await with try/catch blocks.",
                    "file_path": fp,
                    "line_start": None,
                    "line_end": None,
                    "confidence_score": 0.8,
                })
            if "console.log" in code and "logger" not in code.lower():
                fallbacks.append({
                    "issue_type": "code_smell",
                    "severity": "low",
                    "title": f"Using console.log instead of structured logging in {fp.split('/')[-1]}",
                    "description": f"File '{fp}' uses console.log() for output. In production, console.log lacks log levels, timestamps, and structured formatting. This makes it impossible to filter logs by severity or search them effectively.",
                    "fix_suggestion": "Replace console.log with a structured logging library like Winston or Pino. Use appropriate log levels: logger.info(), logger.warn(), logger.error().",
                    "file_path": fp,
                    "line_start": None,
                    "line_end": None,
                    "confidence_score": 0.85,
                })

        if lang == "Python":
            if "except Exception" in code or "except:" in code:
                fallbacks.append({
                    "issue_type": "code_smell",
                    "severity": "medium",
                    "title": f"Broad exception catching in {fp.split('/')[-1]}",
                    "description": f"File '{fp}' uses bare 'except:' or 'except Exception' which catches ALL exceptions including KeyboardInterrupt and SystemExit. This hides real bugs and makes debugging nearly impossible.",
                    "fix_suggestion": "Catch specific exceptions: 'except (ValueError, KeyError) as e:' instead of broad 'except Exception'. Log the exception details with logger.exception().",
                    "file_path": fp,
                    "line_start": None,
                    "line_end": None,
                    "confidence_score": 0.85,
                })
            if "import *" in code:
                fallbacks.append({
                    "issue_type": "code_smell",
                    "severity": "low",
                    "title": f"Wildcard import (import *) in {fp.split('/')[-1]}",
                    "description": f"File '{fp}' uses wildcard imports which pollute the namespace, make it unclear where names come from, and can cause subtle naming conflicts.",
                    "fix_suggestion": "Replace 'from module import *' with explicit imports: 'from module import ClassA, function_b'.",
                    "file_path": fp,
                    "line_start": None,
                    "line_end": None,
                    "confidence_score": 0.9,
                })

        # Language-agnostic checks
        if "TODO" in code or "FIXME" in code or "HACK" in code:
            tag = "TODO" if "TODO" in code else ("FIXME" if "FIXME" in code else "HACK")
            fallbacks.append({
                "issue_type": "code_smell",
                "severity": "low",
                "title": f"Unresolved {tag} comment in {fp.split('/')[-1]}",
                "description": f"File '{fp}' contains {tag} comments indicating incomplete or temporary code. These should be tracked as tickets and resolved before production deployment.",
                "fix_suggestion": f"Review each {tag} comment, create a tracking issue for it, and either fix it now or document why it's deferred.",
                "file_path": fp,
                "line_start": None,
                "line_end": None,
                "confidence_score": 0.9,
            })

        # Check for hardcoded values
        has_hardcoded = False
        for pattern in ["http://localhost", "127.0.0.1", "password", "secret"]:
            if pattern in code.lower() and pattern not in fp.lower():
                has_hardcoded = True
                break
        if has_hardcoded:
            fallbacks.append({
                "issue_type": "security",
                "severity": "medium",
                "title": f"Potential hardcoded configuration in {fp.split('/')[-1]}",
                "description": f"File '{fp}' contains what appears to be hardcoded configuration values (localhost URLs, credentials, or secrets). These should be externalized to environment variables or a configuration file.",
                "fix_suggestion": "Move hardcoded values to environment variables using os.getenv() (Python) or process.env (Node.js). Use a .env file for local development.",
                "file_path": fp,
                "line_start": None,
                "line_end": None,
                "confidence_score": 0.75,
            })

        # Check for long functions (rough estimate)
        lines = code.split("\n")
        if len(lines) > 80:
            fallbacks.append({
                "issue_type": "improvement",
                "severity": "low",
                "title": f"Large code block in {fp.split('/')[-1]} ({len(lines)} lines)",
                "description": f"File '{fp}' contains a code chunk of {len(lines)} lines. Long files are harder to maintain, test, and debug. Consider splitting into smaller, focused modules.",
                "fix_suggestion": "Extract related functionality into separate helper functions or modules. Each function should ideally do one thing and be under 30-40 lines.",
                "file_path": fp,
                "line_start": None,
                "line_end": None,
                "confidence_score": 0.7,
            })

    # Deduplicate by title
    seen = set()
    unique = []
    for fb in fallbacks:
        if fb["title"] not in seen:
            seen.add(fb["title"])
            fb["issue_hash"] = _generate_issue_hash(repo_id, fb["file_path"], fb["title"], None)
            unique.append(fb)

    logger.info("  🔄 Generated %d fallback improvements", len(unique))
    return unique[:5]  # Cap at 5


async def _get_or_generate_file_summary(db, repo_id: int, chunk: dict) -> dict:
    """Generate or retrieve a cached functional summary of a file."""
    file_path = chunk["file_path"]
    content = chunk["content"]
    file_hash = hashlib.sha256(content.encode()).hexdigest()
    
    # Check cache
    cursor = await db.execute(
        "SELECT summary FROM file_summaries WHERE repo_id = ? AND file_path = ? AND file_hash = ?",
        (repo_id, file_path, file_hash)
    )
    row = await cursor.fetchone()
    if row:
        logger.info("  ⚡ Using cached summary for %s", file_path)
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            pass # Fallback to regenerate
            
    # Need to generate summary
    logger.info("  📝 Generating LLM summary for %s", file_path)
    prompt = SUMMARIZATION_PROMPT.format(
        file_path=file_path,
        language=chunk["language"],
        code=content[:8000]
    )
    
    try:
        raw_response = await _call_llm_with_retry(prompt, retries=2)
        summaries = _parse_llm_response(raw_response)
        summary_obj = summaries[0] if summaries else None
        
        if not summary_obj or not summary_obj.get("purpose"):
            # Fallback simple summary
            summary_obj = {
                "purpose": f"Standard {chunk['language']} file.",
                "key_functions": ["Unknown"],
                "dependencies": ["Unknown"]
            }
            
        summary_json = json.dumps(summary_obj)
        
        # Upsert into DB
        await db.execute("""
            INSERT INTO file_summaries (repo_id, file_path, summary, file_hash)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(repo_id, file_path) 
            DO UPDATE SET summary=excluded.summary, file_hash=excluded.file_hash, last_updated=CURRENT_TIMESTAMP
        """, (repo_id, file_path, summary_json, file_hash))
        await db.commit()
        
        return summary_obj
        
    except Exception as e:
        logger.warning("  ⚠ Failed to generate summary for %s: %s", file_path, str(e))
        return {
            "purpose": "Failed to analyze this file.",
            "key_functions": [],
            "dependencies": []
        }


async def run_analysis_pipeline(repo_id: int):
    """
    Three-phase autonomous analysis pipeline with guaranteed output.
    Phase 1: Strict bug detection
    Phase 2: Improvement mode (if Phase 1 found < 3 issues)
    Phase 3: Cross-file architectural analysis
    Fallback: Deterministic code pattern scanning
    """
    db = await get_db()

    # Debug counters
    debug_stats = {
        "total_chunks": 0,
        "filtered_chunks": 0,
        "skipped_chunks": 0,
        "batches_processed": 0,
        "llm_calls": 0,
        "llm_successes": 0,
        "llm_failures": 0,
        "parse_successes": 0,
        "parse_failures": 0,
        "phase1_issues": 0,
        "phase2_issues": 0,
        "phase3_issues": 0,
        "fallback_issues": 0,
    }

    try:
        # ── Mark analyzing ──
        logger.info("=" * 60)
        logger.info("🔍 STARTING AI ANALYSIS v3 for repo_id=%d", repo_id)
        logger.info("=" * 60)
        await db.execute(
            "UPDATE repositories SET analysis_status = 'analyzing' WHERE id = ?",
            (repo_id,)
        )
        await db.commit()

        # ── Clear old issues for re-analysis ──
        await db.execute("DELETE FROM code_issues WHERE repo_id = ?", (repo_id,))
        await db.commit()
        logger.info("🗑️ Cleared old issues for fresh analysis")

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
                "UPDATE repositories SET analysis_status = 'analyzed', summary_message = '⚠️ No code files found to analyze. Try a different repository.' WHERE id = ?",
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

        debug_stats["total_chunks"] = len(rows)
        debug_stats["filtered_chunks"] = len(chunks)
        debug_stats["skipped_chunks"] = skipped

        logger.info("📊 Stats: %d total chunks, %d after filtering, %d skipped",
                     len(rows), len(chunks), skipped)

        if not chunks:
            logger.warning("All chunks were filtered out for repo_id=%d", repo_id)
            await db.execute(
                "UPDATE repositories SET analysis_status = 'analyzed', summary_message = '⚠️ No analyzable code files found (all filtered). Try a repository with source code.' WHERE id = ?",
                (repo_id,)
            )
            await db.commit()
            return

        # ── FILE SUMMARIZATION LAYER (TOP 10 FILES) ──
        logger.info("─" * 50)
        logger.info("📂 SUMMARIZATION LAYER: Processing up to 10 key files")
        logger.info("─" * 50)
        
        file_summaries_cache = {}
        for chunk in chunks[:10]:
            fp = chunk["file_path"]
            if fp not in file_summaries_cache:
                debug_stats["llm_calls"] += 1
                try:
                    smry = await _get_or_generate_file_summary(db, repo_id, chunk)
                    file_summaries_cache[fp] = smry
                    debug_stats["llm_successes"] += 1
                except Exception as e:
                    debug_stats["llm_failures"] += 1
                    if "RATE_LIMIT_EXCEEDED" in str(e):
                        logger.error("  🚨 Rate limit hit during summarization!")
                        # We will just continue and let the rest of the pipeline handle rate limits as well
                        pass

        # ── PHASE 1: Strict Bug Detection ──
        logger.info("─" * 50)
        logger.info("🔬 PHASE 1: Strict Bug Detection (%d chunks in batches of %d)",
                     len(chunks), BATCH_SIZE)
        logger.info("─" * 50)
        all_issues = []
        seen_hashes = set()
        rate_limit_hit = False

        for batch_start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[batch_start:batch_start + BATCH_SIZE]
            debug_stats["batches_processed"] += 1

            combined_code = ""
            file_context = set()
            for chunk in batch:
                file_context.add(chunk["file_path"])
                combined_code += f"\n// === FILE: {chunk['file_path']} ({chunk['language']}) ===\n"
                combined_code += _add_line_numbers(chunk["content"]) + "\n"

            file_list = ", ".join(file_context)
            logger.info("  📦 Batch %d: analyzing [%s]", debug_stats["batches_processed"], file_list)

            prompt = STRICT_PROMPT.format(
                file_path=file_list,
                language=batch[0]["language"],
                code=combined_code[:10000],  # Increased from 8000
            )

            try:
                debug_stats["llm_calls"] += 1
                raw_response = await _call_llm_with_retry(prompt)
                debug_stats["llm_successes"] += 1

                issues = _parse_llm_response(raw_response)
                if issues:
                    debug_stats["parse_successes"] += 1
                else:
                    debug_stats["parse_failures"] += 1
                    logger.info("  ℹ️ Phase 1 batch %d: LLM returned no parseable issues",
                                debug_stats["batches_processed"])

                for issue in issues:
                    if not _validate_issue(issue):
                        logger.debug("  ⏭ Skipped invalid issue: %s", issue.get("title", "?")[:50])
                        continue
                    issue["severity"] = _normalize_severity(issue)
                    issue["issue_type"] = issue.get("issue_type", "code_smell").lower().strip()
                    valid_types = {"bug", "security", "performance", "code_smell", "improvement"}
                    if issue["issue_type"] not in valid_types:
                        issue["issue_type"] = "code_smell"
                    if not issue.get("file_path") or issue["file_path"] == "{file_path}":
                        issue["file_path"] = list(file_context)[0] if file_context else "unknown"
                    # Ensure confidence score is valid float
                    try:
                        cs = float(issue.get("confidence_score", 0.8))
                        issue["confidence_score"] = max(0.0, min(1.0, cs))
                    except (ValueError, TypeError):
                        issue["confidence_score"] = 0.8

                    issue_hash = _generate_issue_hash(repo_id, issue["file_path"], issue["title"], issue.get("line_start"))
                    if issue_hash in seen_hashes:
                        continue
                    seen_hashes.add(issue_hash)
                    issue["issue_hash"] = issue_hash
                    all_issues.append(issue)

            except Exception as e:
                debug_stats["llm_failures"] += 1
                logger.error("  ✗ Batch %d failed: %s", debug_stats["batches_processed"], str(e))
                if "RATE_LIMIT_EXCEEDED" in str(e):
                    rate_limit_hit = True
                    break
                continue

            # Rate limiting: wait between batches
            await asyncio.sleep(1.5)

        debug_stats["phase1_issues"] = len(all_issues)
        logger.info("🔬 Phase 1 complete: %d strict issues found in %d batches",
                     len(all_issues), debug_stats["batches_processed"])

        # ── PHASE 2: Improvement Mode (if Phase 1 found < 3 issues) ──
        if len(all_issues) < 3 and not rate_limit_hit:
            logger.info("─" * 50)
            logger.info("💡 PHASE 2: Improvement Mode (Phase 1 found only %d issues)", len(all_issues))
            logger.info("─" * 50)

            # Take top priority files for improvement analysis
            top_files = {}
            for chunk in chunks:
                fp = chunk["file_path"]
                if fp not in top_files:
                    top_files[fp] = chunk
                if len(top_files) >= 4:  # Increased from 3 to analyze more files
                    break

            for fp, chunk in top_files.items():
                logger.info("  🔍 Analyzing improvements for: %s", fp)
                prompt = IMPROVEMENT_PROMPT.format(
                    file_path=fp,
                    language=chunk["language"],
                    code=_add_line_numbers(chunk["content"][:8000]),
                )

                try:
                    debug_stats["llm_calls"] += 1
                    raw_response = await _call_llm_with_retry(prompt)
                    debug_stats["llm_successes"] += 1

                    issues = _parse_llm_response(raw_response)
                    if issues:
                        debug_stats["parse_successes"] += 1
                    else:
                        debug_stats["parse_failures"] += 1

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
                        try:
                            cs = float(issue.get("confidence_score", 0.7))
                            issue["confidence_score"] = max(0.0, min(1.0, cs))
                        except (ValueError, TypeError):
                            issue["confidence_score"] = 0.7

                        issue_hash = _generate_issue_hash(repo_id, fp, issue["title"], issue.get("line_start"))
                        if issue_hash in seen_hashes:
                            continue
                        seen_hashes.add(issue_hash)
                        issue["issue_hash"] = issue_hash
                        all_issues.append(issue)

                except Exception as e:
                    debug_stats["llm_failures"] += 1
                    logger.error("  ✗ Improvement scan failed for %s: %s", fp, str(e))
                    if "RATE_LIMIT_EXCEEDED" in str(e):
                        rate_limit_hit = True
                        break

                await asyncio.sleep(1.5)

            debug_stats["phase2_issues"] = len(all_issues) - debug_stats["phase1_issues"]
            logger.info("💡 Phase 2 complete: added %d improvements (total now %d)",
                        debug_stats["phase2_issues"], len(all_issues))

        # ── PHASE 3: Cross-File Architecture Analysis ──
        if not rate_limit_hit:
            logger.info("─" * 50)
            logger.info("🏗️ PHASE 3: Cross-File Architecture Analysis")
            logger.info("─" * 50)

            try:
                # Get repo info
                repo_cursor = await db.execute(
                    "SELECT name, languages, total_files FROM repositories WHERE id = ?",
                    (repo_id,)
                )
                repo_info = await repo_cursor.fetchone()

                # Build context from the summarization layer
                summaries_text = ""
                excerpt_files = []
                for max_i, chunk in enumerate(chunks[:10]):
                    fp = chunk["file_path"]
                    if fp not in excerpt_files:
                        excerpt_files.append(fp)
                        smry = file_summaries_cache.get(fp)
                        if smry:
                            summaries_text += f"\n// ─── {fp} ───\n"
                            summaries_text += json.dumps(smry, indent=2) + "\n"

                if repo_info and excerpt_files:
                    prompt = ARCHITECTURE_PROMPT.format(
                        repo_name=repo_info[0],
                        languages=repo_info[1] or "Unknown",
                        total_files=repo_info[2] or 0,
                        file_summaries=summaries_text,
                    )

                    debug_stats["llm_calls"] += 1
                    raw_response = await _call_llm_with_retry(prompt)
                    debug_stats["llm_successes"] += 1
                    arch_issues = _parse_llm_response(raw_response)

                    arch_added = 0
                    for issue in arch_issues:
                        if not _validate_issue(issue):
                            continue
                        issue["issue_type"] = "improvement"
                        issue["severity"] = issue.get("severity", "medium").lower().strip()
                        if issue["severity"] not in {"critical", "high", "medium", "low"}:
                            issue["severity"] = "medium"
                        issue["file_path"] = "architecture"
                        try:
                            cs = float(issue.get("confidence_score", 0.7))
                            issue["confidence_score"] = max(0.0, min(1.0, cs))
                        except (ValueError, TypeError):
                            issue["confidence_score"] = 0.7

                        issue_hash = _generate_issue_hash(repo_id, "architecture", issue["title"], None)
                        if issue_hash in seen_hashes:
                            continue
                        seen_hashes.add(issue_hash)
                        issue["issue_hash"] = issue_hash
                        all_issues.append(issue)
                        arch_added += 1

                    debug_stats["phase3_issues"] = arch_added
                    logger.info("🏗️ Phase 3 complete: added %d architectural insights", arch_added)

            except Exception as e:
                debug_stats["llm_failures"] += 1
                logger.warning("  ⚠ Architecture analysis failed: %s", str(e))
                if "RATE_LIMIT_EXCEEDED" in str(e):
                    rate_limit_hit = True

        # ── FALLBACK: Guaranteed minimum output ──
        if len(all_issues) < 3:
            logger.info("─" * 50)
            logger.info("🔄 FALLBACK: Generating pattern-based improvements (%d issues so far)",
                        len(all_issues))
            logger.info("─" * 50)

            fallbacks = _generate_fallback_improvements(chunks, repo_id)
            for fb in fallbacks:
                if fb["issue_hash"] not in seen_hashes:
                    seen_hashes.add(fb["issue_hash"])
                    all_issues.append(fb)
                    debug_stats["fallback_issues"] += 1

            logger.info("🔄 Fallback complete: added %d pattern-based improvements",
                        debug_stats["fallback_issues"])

        # ── Store issues in DB ──
        logger.info("─" * 50)
        logger.info("💾 Storing %d total issues", len(all_issues))
        stored_count = 0
        for issue in all_issues:
            try:
                await db.execute("""
                    INSERT OR IGNORE INTO code_issues
                    (repo_id, file_path, issue_type, severity, title, description,
                     fix_suggestion, impact, why_it_matters, line_start, line_end, 
                     confidence_score, priority_score, issue_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    repo_id,
                    issue["file_path"],
                    issue["issue_type"],
                    issue["severity"],
                    issue["title"],
                    issue["description"],
                    issue.get("fix_suggestion", ""),
                    issue.get("impact", ""),
                    issue.get("why_it_matters", ""),
                    issue.get("line_start"),
                    issue.get("line_end"),
                    float(issue.get("confidence_score", 0.8)),
                    float(issue.get("priority_score", 0.0)),
                    issue["issue_hash"],
                ))
                stored_count += 1
            except Exception as e:
                logger.warning("  ✗ Failed to store issue '%s': %s", issue.get("title", "?"), str(e))

        await db.commit()
        logger.info("💾 Stored %d issues (of %d)", stored_count, len(all_issues))

        # ── Generate smart summary ──
        sev_cursor = await db.execute("""
            SELECT severity, COUNT(*) FROM code_issues
            WHERE repo_id = ? AND is_false_positive = 0
            GROUP BY severity
        """, (repo_id,))
        severity_counts = dict(await sev_cursor.fetchall())

        type_cursor = await db.execute("""
            SELECT issue_type, COUNT(*) FROM code_issues
            WHERE repo_id = ? AND is_false_positive = 0
            GROUP BY issue_type
        """, (repo_id,))
        type_counts = dict(await type_cursor.fetchall())

        critical = severity_counts.get("critical", 0)
        high = severity_counts.get("high", 0)
        medium = severity_counts.get("medium", 0)
        low = severity_counts.get("low", 0)
        total = critical + high + medium + low

        bug_count = type_counts.get("bug", 0) + type_counts.get("security", 0)
        improvement_count = type_counts.get("improvement", 0) + type_counts.get("code_smell", 0)

        # Smart summary message — NEVER says "no issues found"
        if rate_limit_hit:
            summary = f"⚠️ Analysis paused due to AI rate limits. Found {total} issues so far. Re-run later for complete results."
        elif critical > 0 or high > 0:
            summary = f"🔴 Found {total} issues: {critical} critical, {high} high priority. {improvement_count} improvements suggested."
        elif bug_count > 0:
            summary = f"🟡 Found {bug_count} potential bugs and {improvement_count} improvements across your codebase."
        elif total > 0:
            summary = f"✅ No critical bugs found! 💡 Discovered {total} improvements to strengthen your code quality."
        else:
            summary = f"✅ Code passed strict analysis. 💡 Review the {len(chunks)} analyzed files for manual optimization opportunities."

        await db.execute(
            "UPDATE repositories SET analysis_status = 'analyzed', summary_message = ? WHERE id = ?",
            (summary, repo_id)
        )
        await db.commit()

        # ── Final debug summary ──
        logger.info("=" * 60)
        logger.info("✅ ANALYSIS COMPLETE for repo_id=%d", repo_id)
        logger.info("   %s", summary)
        logger.info("─" * 40)
        logger.info("   📊 Debug Stats:")
        logger.info("      Chunks: %d total, %d analyzed, %d skipped",
                     debug_stats["total_chunks"], debug_stats["filtered_chunks"],
                     debug_stats["skipped_chunks"])
        logger.info("      Batches: %d processed", debug_stats["batches_processed"])
        logger.info("      LLM Calls: %d total, %d success, %d failed",
                     debug_stats["llm_calls"], debug_stats["llm_successes"],
                     debug_stats["llm_failures"])
        logger.info("      Parse: %d success, %d failures",
                     debug_stats["parse_successes"], debug_stats["parse_failures"])
        logger.info("      Issues: P1=%d, P2=%d, P3=%d, Fallback=%d, Total=%d",
                     debug_stats["phase1_issues"], debug_stats["phase2_issues"],
                     debug_stats["phase3_issues"], debug_stats["fallback_issues"],
                     len(all_issues))
        logger.info("=" * 60)

    except Exception as e:
        logger.error("❌ ANALYSIS PIPELINE FAILED for repo_id=%d: %s", repo_id, str(e))
        await db.execute(
            "UPDATE repositories SET analysis_status = 'failed', summary_message = ? WHERE id = ?",
            (f"Analysis failed: {str(e)[:200]}", repo_id)
        )
        await db.commit()
    finally:
        await db.close()
