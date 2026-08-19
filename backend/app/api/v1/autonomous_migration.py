from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, status
from redis.asyncio import Redis

from app.core.database import get_redis
from app.core.deps import CurrentUser, DbSession
from app.core.prompts import DEFAULT_CONTEXT_RULE
from app.models import JobStatus, MigrationJob, UserRole
from app.schemas.autonomous import (
    AutonomousJobDetail,
    AutonomousRunRequest,
    AutonomousRunResponse,
)
from app.services.git_sandbox import GitSandboxService
from app.services.migration_service import STATE_KEY
from app.services.queue import enqueue_autonomous_migration
from app.services.repositories import JobRepository, ProjectRepository

router = APIRouter()


@router.post(
    "/run",
    response_model=AutonomousRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_autonomous_migration(
    payload: AutonomousRunRequest, session: DbSession, user: CurrentUser
) -> AutonomousRunResponse:
    """Clone a repo, run its tests, refactor, heal, and open a PR."""
    try:
        GitSandboxService.validate_repo_url(payload.repo_url)
    except Exception as exc:  # surface friendly validation errors.
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Resolve or create a project so the run shows up in the jobs UI.
    projects = ProjectRepository(session)
    project = await projects.get_by_owner_and_repo_url(user.id, payload.repo_url)
    if project is None:
        project = await projects.create(
            owner_id=user.id,
            name=f"{payload.repo_owner}/{payload.repo_name}",
            description=f"Autonomous migration of {payload.repo_url}",
            repo_url=payload.repo_url,
            source_language="python",
            target_stack="python-3.12",
        )
        await session.flush()

    jobs = JobRepository(session)
    job = await jobs.create(
        project_id=project.id,
        title=f"Autonomous migration: {payload.repo_owner}/{payload.repo_name}",
        context_rule=payload.context_rule or DEFAULT_CONTEXT_RULE,
        input_code=(
            f"# Autonomous git-driven migration job\n"
            f"# repo_url: {payload.repo_url}\n"
            f"# branch: {payload.base_branch}\n"
        ),
    )
    job.metrics = {
        "kind": "autonomous-git",
        "repo_url": payload.repo_url,
        "repo_owner": payload.repo_owner,
        "repo_name": payload.repo_name,
        "base_branch": payload.base_branch,
        "branch_name": None,
        "pull_request_url": None,
        "pull_request_number": None,
        "files_changed": 0,
    }
    await session.commit()
    await session.refresh(job)

    try:
        await enqueue_autonomous_migration(
            job_id=job.id,
            repo_url=payload.repo_url,
            repo_owner=payload.repo_owner,
            repo_name=payload.repo_name,
            github_token=payload.github_token,
            context_rule=payload.context_rule,
            base_branch=payload.base_branch,
            title=payload.title,
            body=payload.body,
        )
    except Exception:
        job.status = JobStatus.failed.value
        job.error_message = "Failed to enqueue autonomous job: task queue unavailable."
        await session.commit()
        await session.refresh(job)
        raise HTTPException(
            status_code=503,
            detail="Task queue unavailable; autonomous migration could not be started.",
        ) from None

    return AutonomousRunResponse(
        job_id=job.id,
        project_id=project.id,
        status=job.status,
        message="Autonomous migration queued. Track progress via /jobs/{id}/status.",
    )


@router.get("/jobs/{job_id}", response_model=AutonomousJobDetail)
async def get_autonomous_job(
    job_id: int, session: DbSession, user: CurrentUser
) -> AutonomousJobDetail:
    """Return live status and result details for an autonomous job."""
    job = await session.get(MigrationJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    project = await ProjectRepository(session).get_by_id(job.project_id)
    if project is None or (project.owner_id != user.id and user.role != UserRole.admin):
        raise HTTPException(status_code=403, detail="Access denied.")

    redis: Redis = await get_redis()
    live = None
    raw = await redis.get(STATE_KEY.format(job_id=job.id))
    if raw:
        try:
            live = json.loads(raw)
        except json.JSONDecodeError:
            live = None

    status_value = live["status"] if live else job.status
    progress = int(live.get("progress", 0)) if live else None
    message = live.get("message") if live else None

    return AutonomousJobDetail(
        job_id=job.id,
        status=status_value,
        progress=progress,
        message=message,
        pull_request_url=job.metrics.get("pull_request_url") if job.metrics else None,
        branch_name=job.metrics.get("branch_name") if job.metrics else None,
        error_message=job.error_message,
        diff_summary=job.diff,
    )
