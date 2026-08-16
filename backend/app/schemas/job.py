from datetime import datetime

from pydantic import BaseModel, Field


class JobSubmitRequest(BaseModel):
    project_id: int
    title: str = Field(min_length=1, max_length=255)
    context_rule: str | None = Field(default=None, max_length=10000)
    input_code: str = Field(min_length=1, max_length=2_000_000)


class JobCreate(BaseModel):
    project_id: int
    title: str = Field(min_length=1, max_length=255)
    context_rule: str | None = None
    input_code: str = Field(min_length=1)


class JobUpdate(BaseModel):
    status: str | None = None
    output_code: str | None = None
    diff: str | None = None
    findings: list | None = None
    error_message: str | None = None
    metrics: dict | None = None


class FindingItem(BaseModel):
    line: int | None = None
    severity: str = "info"
    category: str
    message: str
    suggestion: str | None = None


class JobStatusRead(BaseModel):
    id: int
    project_id: int
    title: str
    status: str
    self_heal_attempts: int
    error_message: str | None
    progress: int | None = None
    message: str | None = None
    created_at: datetime
    updated_at: datetime


class JobRead(BaseModel):
    id: int
    project_id: int
    title: str
    context_rule: str
    status: str
    input_code: str
    output_code: str | None
    diff: str | None
    findings: list
    self_heal_attempts: int
    error_message: str | None
    metrics: dict
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
