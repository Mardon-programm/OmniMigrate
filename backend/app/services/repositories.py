from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MigrationJob, Project, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, email: str, hashed_password: str, full_name: str, role) -> User:
        user = User(email=email, hashed_password=hashed_password, full_name=full_name, role=role)
        self.session.add(user)
        await self.session.flush()
        return user

    async def list_all(self, offset: int = 0, limit: int = 100) -> list[User]:
        result = await self.session.execute(
            select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, user: User) -> User:
        await self.session.flush()
        return user


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, project_id: int) -> Project | None:
        return await self.session.get(Project, project_id)

    async def get_by_owner_and_repo_url(self, owner_id: int, repo_url: str) -> Project | None:
        result = await self.session.execute(
            select(Project).where(Project.owner_id == owner_id, Project.repo_url == repo_url)
        )
        return result.scalars().first()

    async def list_for_owner(
        self, owner_id: int, offset: int = 0, limit: int = 100
    ) -> list[Project]:
        result = await self.session.execute(
            select(Project)
            .where(Project.owner_id == owner_id)
            .order_by(Project.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_all(self, offset: int = 0, limit: int = 100) -> list[Project]:
        result = await self.session.execute(
            select(Project).order_by(Project.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def count_jobs(self, project_id: int) -> int:
        result = await self.session.execute(
            select(sa.func.count(MigrationJob.id)).where(MigrationJob.project_id == project_id)
        )
        return int(result.scalar_one())

    async def create(
        self,
        owner_id: int,
        name: str,
        description: str | None,
        repo_url: str | None,
        source_language: str,
        target_stack: str,
    ) -> Project:
        project = Project(
            owner_id=owner_id,
            name=name,
            description=description,
            repo_url=repo_url,
            source_language=source_language,
            target_stack=target_stack,
        )
        self.session.add(project)
        await self.session.flush()
        return project


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, job_id: int) -> MigrationJob | None:
        return await self.session.get(MigrationJob, job_id)

    async def list_for_project(
        self, project_id: int, offset: int = 0, limit: int = 100
    ) -> list[MigrationJob]:
        result = await self.session.execute(
            select(MigrationJob)
            .where(MigrationJob.project_id == project_id)
            .order_by(MigrationJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_all(self, offset: int = 0, limit: int = 100) -> list[MigrationJob]:
        result = await self.session.execute(
            select(MigrationJob)
            .order_by(MigrationJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_for_owner(
        self, owner_id: int, offset: int = 0, limit: int = 100
    ) -> list[MigrationJob]:
        result = await self.session.execute(
            select(MigrationJob)
            .join(Project, Project.id == MigrationJob.project_id)
            .where(Project.owner_id == owner_id)
            .order_by(MigrationJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(
        self,
        project_id: int,
        title: str,
        context_rule: str,
        input_code: str,
    ) -> MigrationJob:
        job = MigrationJob(
            project_id=project_id,
            title=title,
            context_rule=context_rule,
            input_code=input_code,
        )
        self.session.add(job)
        await self.session.flush()
        return job
