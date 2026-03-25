"""
Analysis API routes.
Exposes endpoints for retrieving AI-detected code issues,
file listings with issue counts, and repo analysis summaries.
"""
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.database.db import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/repository", tags=["Analysis"])


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
        query = "SELECT * FROM code_issues WHERE repo_id = ? AND is_false_positive = 0"
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

        # Order: critical first, then high, medium, low
        query += """
            ORDER BY
                CASE severity
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                END,
                created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        issues = []
        for row in rows:
            issues.append({
                "id": row[0],
                "repo_id": row[1],
                "file_path": row[2],
                "issue_type": row[3],
                "severity": row[4],
                "title": row[5],
                "description": row[6],
                "fix_suggestion": row[7],
                "line_start": row[8],
                "line_end": row[9],
                "confidence_score": row[10],
                "is_false_positive": bool(row[11]),
                "status": row[13],
                "created_at": row[14],
            })

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
        # Get repo info
        repo_cursor = await db.execute(
            "SELECT name, url, status, analysis_status, summary_message, total_files, languages FROM repositories WHERE id = ?",
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

        total_issues = sum(severity_counts.values())

        return {
            "repo_id": repo_id,
            "name": repo[0],
            "url": repo[1],
            "indexing_status": repo[2],
            "analysis_status": repo[3],
            "summary_message": repo[4],
            "total_files": repo[5],
            "languages": repo[6],
            "total_issues": total_issues,
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
        }
    finally:
        await db.close()
