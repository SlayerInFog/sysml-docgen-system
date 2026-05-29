from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TemplateCreate(BaseModel):
    project_id: int | None = None
    name: str
    description: str | None = None
    content: str
    branch_name: str | None = None
    version_tag: str | None = None


class TemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    content: str | None = None
    branch_name: str | None = None
    version_tag: str | None = None


class TemplatePreviewRequest(BaseModel):
    title: str = "模板预览文档"
    content: str


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    project_id: int | None
    name: str
    description: str | None
    content: str
    version: int
    branch_name: str
    version_tag: str | None
    created_at: datetime


class TemplateVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    template_id: int
    version: int
    name: str
    description: str | None
    content: str
    branch_name: str
    version_tag: str | None
    created_by: int | None
    created_at: datetime


class GenerateDocumentRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    project_id: int
    model_id: int
    template_id: int
    title: str


class GeneratedDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    project_id: int
    model_id: int
    template_id: int
    title: str
    status: str
    html_content: str
    file_path: str | None
    created_by: int
    created_at: datetime
