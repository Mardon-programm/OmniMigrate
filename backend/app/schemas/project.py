from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    repo_url: str | None = Field(default=None, max_length=512)
    source_language: str = Field(default="python", max_length=64)
    target_stack: str = Field(default="python-3.12", max_length=64)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    repo_url: str | None = Field(default=None, max_length=512)
    source_language: str | None = Field(default=None, max_length=64)
    target_stack: str | None = Field(default=None, max_length=64)


class ProjectRead(BaseModel):
    id: int
    owner_id: int
    name: str
    description: str | None
    repo_url: str | None
    source_language: str
    target_stack: str
    created_at: datetime
    updated_at: datetime
    job_count: int = 0

    model_config = {"from_attributes": True}
