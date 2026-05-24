from datetime import datetime

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    code: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ProjectMemberCreate(BaseModel):
    user_id: int
    role: str = "viewer"


class ProjectMemberUpdate(BaseModel):
    role: str


class ProjectMemberOut(BaseModel):
    id: int
    project_id: int
    user_id: int
    username: str
    full_name: str | None
    email: str
    role: str
    created_at: datetime


class ProjectOut(BaseModel):
    id: int
    name: str
    code: str
    description: str | None
    owner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
