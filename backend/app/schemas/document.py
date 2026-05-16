from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TemplateCreate(BaseModel):
    project_id: int | None = None
    name: str
    description: str | None = None
    content: str


class TemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    content: str | None = None


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    project_id: int | None
    name: str
    description: str | None
    content: str
    version: int
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
