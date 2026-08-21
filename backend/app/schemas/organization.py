from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.organization import OrgRole


class OrgCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9\-]+$")
    description: str | None = None


class OrgUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class OrgRead(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class OrgMemberInvite(BaseModel):
    user_id: int
    role: OrgRole = OrgRole.member


class OrgMemberUpdate(BaseModel):
    role: OrgRole | None = None
    is_active: bool | None = None


class OrgMemberRead(BaseModel):
    id: int
    organization_id: int
    user_id: int
    role: OrgRole
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class AuditLogRead(BaseModel):
    id: int
    organization_id: int | None
    user_id: int | None
    action: str
    resource_type: str
    resource_id: str | None
    detail: str | None
    ip_address: str | None
    created_at: datetime
    model_config = {"from_attributes": True}
