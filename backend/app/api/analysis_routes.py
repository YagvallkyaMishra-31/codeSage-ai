"""
Analysis API routes.
Exposes endpoints for retrieving AI-detected code issues,
file listings with issue counts, and repo analysis summaries.
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.database.db import get_db
from app.services.analysis_service import safe_analysis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/repository", tags=["Analysis"])


@router.post("/{repo_id}/reanalyze")
async def reanalyze_repo(repo_id: int):
    """Re-trigger AI analysis on an already-indexed repository."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, name, status FROM repositories WHERE id = ?", (repo_id,)
        )
        repo = await cursor.fetchone()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        if repo[2] not in ("completed", "failed"):
            raise HTTPException(
                status_code=409,
                detail="Repository is still being indexed. Wait for indexing to complete."
            )

        # Reset analysis status
        await db.execute(
            "UPDATE repositories SET analysis_status = 'analyzing', summary_message = '', health_score = 100 WHERE id = ?",
            (repo_id,)
        )
        # Clear old issues for fresh analysis
        await db.execute("DELETE FROM code_issues WHERE repo_id = ?", (repo_id,))
        await db.commit()

        # Launch analysis in background
        asyncio.create_task(safe_analysis(repo_id))

        logger.info("Re-analysis triggered for repo_id=%d (%s)", repo_id, repo[1])
        return {
            "message": f"Re-analysis started for '{repo[1]}'. Refresh the page to see progress.",
            "repo_id": repo_id,
            "analysis_status": "analyzing",
        }
    finally:
        await db.close()


def _categorize_issue(issue_dict: dict) -> str:
    """Deterministically categorize an issue based on its content."""
    text = (
        issue_dict.get("title", "") + " " + 
        issue_dict.get("description", "") + " " + 
        issue_dict.get("impact", "")
    ).lower()
    
    if any(k in text for k in ["auth", "login", "jwt", "token", "password", "security", "credential", "bypass"]):
        return "Authentication & Security"
    if any(k in text for k in ["db", "database", "sql", "query", "mongo", "prisma", "orm", "connection"]):
        return "Database & Storage"
    if any(k in text for k in ["api", "route", "endpoint", "fetch", "request", "response", "cors", "status code"]):
        return "API & Routing"
    if issue_dict.get("issue_type") == "performance" or any(k in text for k in ["memory", "slow", "leak", "bottleneck", "optimize"]):
        return "Performance"
    return "Code Quality & Patterns"


@router.get("/{repo_id}/issues")
async def get_repo_issues(
    repo_id: int,
    severity: Optional[str] = Query(None, description="Filter by severity: critical, high, medium, low"),
    issue_type: Optional[str] = Query(None, description="Filter by type: bug, security, performance, code_smell, improvement"),
    file_path: Optional[str] = Query(None, description="Filter by file path"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    """Get all detected issues for a repository with optional filters."""
    db = await get_db()
    try:
        query = """
            SELECT id, repo_id, file_path, issue_type, severity, title, 
                   description, fix_suggestion, impact, why_it_matters, 
                   line_start, line_end, confidence_score, priority_score, 
                   is_false_positive, issue_hash, status, created_at 
            FROM code_issues 
            WHERE repo_id = ? AND is_false_positive = 0
        """
        params = [repo_id]

        if severity:
            query += " AND severity = ?"
            params.append(severity.lower())
        if issue_type:
            query += " AND issue_type = ?"
            params.append(issue_type.lower())
        if file_path:
            query += " AND file_path = ?"
            params.append(file_path)

        # Order by priority_score first, then severity
        query += """
            ORDER BY
                priority_score DESC,
                CASE severity
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                END DESC,
                created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        issues = []
        for row in rows:
            issue_type = row[3]
            file_path = row[2]
            
            # Infer analysis phase from issue characteristics
            if file_path == "architecture":
                analysis_phase = "architecture"
            elif issue_type in ("improvement", "code_smell") and row[4] in ("low", "medium"):
                analysis_phase = "improvement"
            else:
                analysis_phase = "strict"

            issue_dict = {
                "id": row[0],
                "repo_id": row[1],
                "file_path": file_path,
                "issue_type": issue_type,
                "severity": row[4],
                "title": row[5],
                "description": row[6],
                "fix_suggestion": row[7],
                "impact": row[8],
                "why_it_matters": row[9],
                "line_start": row[10],
                "line_end": row[11],
                "confidence_score": row[12],
                "priority_score": row[13],
                "is_false_positive": bool(row[14]),
                "issue_hash": row[15],
                "status": row[16],
                "created_at": row[17],
                "analysis_phase": analysis_phase,
            }
            
            issue_dict["category"] = _categorize_issue(issue_dict)
            issues.append(issue_dict)

        # Get total count
        count_query = "SELECT COUNT(*) FROM code_issues WHERE repo_id = ? AND is_false_positive = 0"
        count_params = [repo_id]
        if severity:
            count_query += " AND severity = ?"
            count_params.append(severity.lower())
        if issue_type:
            count_query += " AND issue_type = ?"
            count_params.append(issue_type.lower())

        count_cursor = await db.execute(count_query, count_params)
        total = (await count_cursor.fetchone())[0]

        return {"issues": issues, "total": total, "limit": limit, "offset": offset}
    finally:
        await db.close()


@router.get("/{repo_id}/files")
async def get_repo_files(repo_id: int):
    """Get all indexed files with issue counts per file."""
    db = await get_db()
    try:
        cursor = await db.execute("""
            SELECT
                fm.id, fm.file_name, fm.file_path, fm.language,
                fm.size_bytes, fm.line_count,
                COALESCE(ic.issue_count, 0) as issue_count,
                COALESCE(ic.critical_count, 0) as critical_count,
                COALESCE(ic.high_count, 0) as high_count
            FROM file_metadata fm
            LEFT JOIN (
                SELECT file_path,
                    COUNT(*) as issue_count,
                    SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) as critical_count,
                    SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) as high_count
                FROM code_issues
                WHERE repo_id = ? AND is_false_positive = 0
                GROUP BY file_path
            ) ic ON fm.file_path = ic.file_path
            WHERE fm.repo_id = ?
            ORDER BY COALESCE(ic.issue_count, 0) DESC, fm.file_path
        """, (repo_id, repo_id))

        rows = await cursor.fetchall()
        files = []
        for row in rows:
            risk = "clean"
            if row[7] > 0:  # critical
                risk = "critical"
            elif row[8] > 0:  # high
                risk = "high"
            elif row[6] > 0:  # any issues
                risk = "medium"

            files.append({
                "id": row[0],
                "file_name": row[1],
                "file_path": row[2],
                "language": row[3],
                "size_bytes": row[4],
                "line_count": row[5],
                "issue_count": row[6],
                "critical_count": row[7],
                "high_count": row[8],
                "risk_level": risk,
            })

        return {"files": files, "total": len(files)}
    finally:
        await db.close()


@router.get("/{repo_id}/summary")
async def get_repo_summary(repo_id: int):
    """Get aggregated analysis summary for a repository."""
    db = await get_db()
    try:
        # Get repo info including health_score
        repo_cursor = await db.execute(
            "SELECT name, url, status, analysis_status, summary_message, total_files, languages, health_score FROM repositories WHERE id = ?",
            (repo_id,)
        )
        repo = await repo_cursor.fetchone()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        # Severity breakdown
        sev_cursor = await db.execute("""
            SELECT severity, COUNT(*) FROM code_issues
            WHERE repo_id = ? AND is_false_positive = 0
            GROUP BY severity
        """, (repo_id,))
        severity_counts = dict(await sev_cursor.fetchall())

        # Type breakdown
        type_cursor = await db.execute("""
            SELECT issue_type, COUNT(*) FROM code_issues
            WHERE repo_id = ? AND is_false_positive = 0
            GROUP BY issue_type
        """, (repo_id,))
        type_counts = dict(await type_cursor.fetchall())

        # Files with most issues
        hotspot_cursor = await db.execute("""
            SELECT file_path, COUNT(*) as cnt FROM code_issues
            WHERE repo_id = ? AND is_false_positive = 0
            GROUP BY file_path ORDER BY cnt DESC LIMIT 5
        """, (repo_id,))
        hotspots = [{"file_path": row[0], "issue_count": row[1]}
                     for row in await hotspot_cursor.fetchall()]

        # Get Top Insights (Architecture patterns)
        insights_cursor = await db.execute("""
            SELECT title, description, impact, why_it_matters, priority_score 
            FROM code_issues 
            WHERE repo_id = ? AND file_path = 'architecture' AND is_false_positive = 0 
            ORDER BY priority_score DESC LIMIT 3
        """, (repo_id,))
        top_insights = [{
            "title": row[0], "description": row[1], 
            "impact": row[2], "why_it_matters": row[3], "priority_score": row[4]
        } for row in await insights_cursor.fetchall()]

        total_issues = sum(severity_counts.values())
        bug_count = type_counts.get("bug", 0) + type_counts.get("security", 0)
        improvement_count = type_counts.get("improvement", 0) + type_counts.get("code_smell", 0)

        # Dynamic health score — NEVER fake 100 unless truly clean
        critical_count = severity_counts.get("critical", 0)
        high_count = severity_counts.get("high", 0)
        medium_count = severity_counts.get("medium", 0)
        
        if repo[3] == "analyzing":
            # Still running — don't show a score yet
            computed_health = None
        elif total_issues == 0 and repo[3] == "analyzed":
            # No issues but analysis completed — might be incomplete
            computed_health = 85
        else:
            computed_health = max(0, 100 - (critical_count * 15) - (high_count * 8) - (medium_count * 3) - (bug_count * 5))
        
        # Use DB value if explicitly set and non-default, otherwise compute
        db_health = repo[7]
        health_score = db_health if (db_health is not None and db_health != 100) else (computed_health or 85)

        return {
            "repo_id": repo_id,
            "name": repo[0],
            "url": repo[1],
            "indexing_status": repo[2],
            "analysis_status": repo[3],
            "summary_message": repo[4],
            "total_files": repo[5],
            "languages": repo[6],
            "health_score": health_score,
            "total_issues": total_issues,
            "bug_count": bug_count,
            "improvement_count": improvement_count,
            "severity_breakdown": {
                "critical": severity_counts.get("critical", 0),
                "high": severity_counts.get("high", 0),
                "medium": severity_counts.get("medium", 0),
                "low": severity_counts.get("low", 0),
            },
            "type_breakdown": {
                "bug": type_counts.get("bug", 0),
                "security": type_counts.get("security", 0),
                "performance": type_counts.get("performance", 0),
                "code_smell": type_counts.get("code_smell", 0),
                "improvement": type_counts.get("improvement", 0),
            },
            "hotspot_files": hotspots,
            "top_insights": top_insights,
        }
    finally:
        await db.close()
