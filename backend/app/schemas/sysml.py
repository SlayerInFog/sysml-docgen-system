from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SysMLModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    project_id: int
    name: str
    description: str | None
    source_filename: str
    version: int
    status: str
    uploaded_by: int
    created_at: datetime


class ModelElementUpdate(BaseModel):
    name: str | None = None
    documentation: str | None = None


class ModelElementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    model_id: int
    element_uid: str
    name: str
    type: str
    documentation: str | None
    parent_uid: str | None


class ModelRelationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    model_id: int
    source_uid: str
    target_uid: str
    relation_type: str
    label: str | None


class ModelGraphOut(BaseModel):
    elements: list[ModelElementOut]
    relations: list[ModelRelationOut]
