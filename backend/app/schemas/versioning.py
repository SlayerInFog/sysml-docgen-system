from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.document import TemplateOut
from app.schemas.sysml import SysMLModelOut


class VersionBranchCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    project_id: int | None = None
    item_type: str
    name: str
    description: str | None = None
    source_model_id: int | None = None
    source_template_id: int | None = None


class VersionTagCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    project_id: int | None = None
    item_type: str
    branch_id: int | None = None
    model_id: int | None = None
    template_id: int | None = None
    name: str
    description: str | None = None


class VersionRollbackCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    project_id: int | None = None
    item_type: str
    branch_id: int
    tag_id: int | None = None
    target_model_id: int | None = None
    target_template_id: int | None = None
    reason: str | None = None


class VersionBranchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    project_id: int | None
    item_type: str
    name: str
    description: str | None
    head_model_id: int | None
    head_template_id: int | None
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    head_model: SysMLModelOut | None = None
    head_template: TemplateOut | None = None


class VersionTagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    project_id: int | None
    item_type: str
    branch_id: int | None
    model_id: int | None
    template_id: int | None
    name: str
    description: str | None
    created_by: int
    created_at: datetime
    model: SysMLModelOut | None = None
    template: TemplateOut | None = None


class VersionRollbackRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    project_id: int | None
    item_type: str
    branch_id: int
    tag_id: int | None
    target_model_id: int | None
    new_model_id: int | None
    target_template_id: int | None
    new_template_id: int | None
    reason: str | None
    created_by: int
    created_at: datetime
    target_model: SysMLModelOut | None = None
    new_model: SysMLModelOut | None = None
    target_template: TemplateOut | None = None
    new_template: TemplateOut | None = None
    tag: VersionTagOut | None = None
