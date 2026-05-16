from datetime import datetime

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    code: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


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
