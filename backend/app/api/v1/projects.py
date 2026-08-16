from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.user import User, UserRole
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.repositories import ProjectRepository

router = APIRouter()


async def _get_owned_project(session, project_id: int, user: User):
    repo = ProjectRepository(session)
    project = await repo.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.owner_id != user.id and user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Access denied.")
    return project


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    session: DbSession,
    user: CurrentUser,
    offset: int = 0,
    limit: int = 100,
) -> list[ProjectRead]:
    repo = ProjectRepository(session)
    projects = await repo.list_for_owner(user.id, offset=offset, limit=limit)
    result = []
    for project in projects:
        item = ProjectRead.model_validate(project)
        item.job_count = await repo.count_jobs(project.id)
        result.append(item)
    return result


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate, session: DbSession, user: CurrentUser
) -> ProjectRead:
    repo = ProjectRepository(session)
    project = await repo.create(
        owner_id=user.id,
        name=payload.name,
        description=payload.description,
        repo_url=payload.repo_url,
        source_language=payload.source_language,
        target_stack=payload.target_stack,
    )
    await session.commit()
    await session.refresh(project)
    item = ProjectRead.model_validate(project)
    item.job_count = 0
    return item


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: int, session: DbSession, user: CurrentUser
) -> ProjectRead:
    project = await _get_owned_project(session, project_id, user)
    repo = ProjectRepository(session)
    item = ProjectRead.model_validate(project)
    item.job_count = await repo.count_jobs(project.id)
    return item


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: int, payload: ProjectUpdate, session: DbSession, user: CurrentUser
) -> ProjectRead:
    project = await _get_owned_project(session, project_id, user)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(project, field, value)
    await session.commit()
    await session.refresh(project)
    repo = ProjectRepository(session)
    item = ProjectRead.model_validate(project)
    item.job_count = await repo.count_jobs(project.id)
    return item


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_project(
    project_id: int,
    session: DbSession,
    user: User = Depends(require_roles(UserRole.admin)),
) -> None:
    repo = ProjectRepository(session)
    project = await repo.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    await session.delete(project)
    await session.commit()
