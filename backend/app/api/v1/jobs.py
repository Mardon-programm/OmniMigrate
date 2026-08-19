from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query, status
from redis.asyncio import Redis

from app.core.database import get_redis
from app.core.deps import CurrentUser, DbSession
from app.core.prompts import DEFAULT_CONTEXT_RULE
from app.models import JobStatus, MigrationJob, User, UserRole
from app.schemas.job import JobRead, JobStatusRead, JobSubmitRequest
from app.services.queue import enqueue_migration_job
from app.services.repositories import JobRepository, ProjectRepository

router = APIRouter()

STATE_KEY = "job:state:{job_id}"


async def _get_job(session, job_id: int, user: User) -> MigrationJob:
    repo = JobRepository(session)
    job = await repo.get_by_id(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if user.role != UserRole.admin:
        project = await ProjectRepository(session).get_by_id(job.project_id)
        if project is None or project.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied.")
    return job


async def _live_state(redis: Redis, job_id: int) -> dict | None:
    raw = await redis.get(STATE_KEY.format(job_id=job_id))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


@router.post("", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
async def submit_migration_job(
    payload: JobSubmitRequest, session: DbSession, user: CurrentUser
) -> JobRead:
    """Create and enqueue a migration job for a project owned by the user."""
    repo = ProjectRepository(session)
    project = await repo.get_by_id(payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.owner_id != user.id and user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Access denied.")

    jobs = JobRepository(session)
    job = await jobs.create(
        project_id=payload.project_id,
        title=payload.title,
        context_rule=payload.context_rule or DEFAULT_CONTEXT_RULE,
        input_code=payload.input_code,
    )
    await session.commit()
    await session.refresh(job)

    try:
        await enqueue_migration_job(job.id)
    except Exception:
        job.status = JobStatus.failed.value
        job.error_message = "Failed to enqueue job: task queue unavailable."
        await session.commit()
        await session.refresh(job)

    return JobRead.model_validate(job)


@router.get("", response_model=list[JobStatusRead])
async def list_jobs(
    session: DbSession,
    user: CurrentUser,
    project_id: int | None = Query(default=None),
    offset: int = 0,
    limit: int = 100,
) -> list[JobStatusRead]:
    """List jobs for the current user, optionally filtered by project."""
    repo = JobRepository(session)
    if project_id is not None:
        project = await ProjectRepository(session).get_by_id(project_id)
        if project is None or (project.owner_id != user.id and user.role != UserRole.admin):
            raise HTTPException(status_code=403, detail="Access denied.")
        jobs = await repo.list_for_project(project_id, offset=offset, limit=limit)
    elif user.role == UserRole.admin:
        jobs = await repo.list_all(offset=offset, limit=limit)
    else:
        jobs = await repo.list_for_owner(user.id, offset=offset, limit=limit)

    redis = await get_redis()
    result = []
    for job in jobs:
        live = await _live_state(redis, job.id)
        result.append(
            JobStatusRead(
                id=job.id,
                project_id=job.project_id,
                title=job.title,
                status=live["status"] if live else job.status,
                self_heal_attempts=job.self_heal_attempts,
                error_message=job.error_message,
                progress=int(live.get("progress", 0)) if live else None,
                message=live.get("message") if live else None,
                created_at=job.created_at,
                updated_at=job.updated_at,
            )
        )
    return result


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: int, session: DbSession, user: CurrentUser) -> JobRead:
    job = await _get_job(session, job_id, user)
    return JobRead.model_validate(job)


@router.get("/{job_id}/status", response_model=JobStatusRead)
async def get_job_status(job_id: int, session: DbSession, user: CurrentUser) -> JobStatusRead:
    """Return real-time job status, preferring the live Redis state."""
    job = await _get_job(session, job_id, user)
    redis = await get_redis()
    live = await _live_state(redis, job_id)
    return JobStatusRead(
        id=job.id,
        project_id=job.project_id,
        title=job.title,
        status=live["status"] if live else job.status,
        self_heal_attempts=job.self_heal_attempts,
        error_message=job.error_message,
        progress=int(live.get("progress", 0)) if live else None,
        message=live.get("message") if live else None,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/{job_id}/diff", response_model=dict)
async def get_job_diff(job_id: int, session: DbSession, user: CurrentUser) -> dict:
    job = await _get_job(session, job_id, user)
    if not job.diff:
        raise HTTPException(status_code=404, detail="No diff available for this job.")
    return {"job_id": job.id, "diff": job.diff}


@router.get("/{job_id}/output", response_model=dict)
async def get_job_output(job_id: int, session: DbSession, user: CurrentUser) -> dict:
    job = await _get_job(session, job_id, user)
    if not job.output_code:
        raise HTTPException(status_code=404, detail="No output available for this job.")
    return {"job_id": job.id, "output_code": job.output_code}


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def cancel_job(job_id: int, session: DbSession, user: CurrentUser) -> None:
    """Cancel a job that is still queued or in progress."""
    job = await _get_job(session, job_id, user)
    if job.status in (
        JobStatus.completed.value,
        JobStatus.failed.value,
        JobStatus.cancelled.value,
    ):
        raise HTTPException(status_code=400, detail="Job is already finished.")
    job.status = JobStatus.cancelled.value
    job.error_message = "Job cancelled by user."
    await session.commit()
    redis = await get_redis()
    await redis.set(
        STATE_KEY.format(job_id=job_id),
        json.dumps(
            {
                "status": JobStatus.cancelled.value,
                "progress": 100,
                "message": "Job cancelled by user.",
            }
        ),
        ex=3600 * 24,
    )
