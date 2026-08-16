from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.deps import CurrentUser, DbSession
from app.models import User, UserRole
from app.schemas.job import JobRead, JobStatusRead, JobSubmitRequest
from app.services.ast_parser import analyze_source
from app.services.diff_utils import diff_stats, generate_diff
from app.services.queue import enqueue_migration_job
from app.services.repositories import JobRepository, ProjectRepository

router = APIRouter()


@router.post("/analyze")
async def analyze_endpoint(payload: dict, user: CurrentUser) -> dict:
    """Dry-run AST analysis of arbitrary source code without creating a job."""
    source = payload.get("code", "")
    if not source:
        raise HTTPException(status_code=422, detail="Field 'code' is required.")
    if len(source) > 2_000_000:
        raise HTTPException(status_code=413, detail="Source code too large.")
    filename = payload.get("filename", "source.py")
    result = analyze_source(filename, source)
    return {
        "success": result.success,
        "findings": result.findings,
        "parse_error": result.parse_error,
    }


@router.post("/preview-diff")
async def preview_diff(payload: dict, user: CurrentUser) -> dict:
    """Preview a diff between provided legacy and modern code snippets."""
    legacy = payload.get("legacy", "")
    modern = payload.get("modern", "")
    filename = payload.get("filename", "source.py")
    diff = generate_diff(legacy, modern, filename)
    return {"diff": diff, "stats": diff_stats(diff).to_dict()}


@router.get("/health")
async def engine_health(user: CurrentUser) -> dict:
    """Return the migration engine capability report."""
    return {
        "engine": "OmniMigrate Core Engine",
        "status": "ready",
        "capabilities": [
            "libcst-ast-analysis",
            "llm-refactoring",
            "sandbox-verification",
            "self-healing-loop",
            "diff-generation",
        ],
    }
