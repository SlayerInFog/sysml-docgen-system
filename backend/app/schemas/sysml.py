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
    branch_name: str
    version_tag: str | None
    status: str
    uploaded_by: int
    created_at: datetime


class SysMLModelUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ModelElementUpdate(BaseModel):
    name: str | None = None
    documentation: str | None = None


class ModelRelationCreate(BaseModel):
    source_uid: str
    target_uid: str
    relation_type: str
    label: str | None = None


class ModelRelationUpdate(BaseModel):
    source_uid: str | None = None
    target_uid: str | None = None
    relation_type: str | None = None
    label: str | None = None


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


class ModelCompareItem(BaseModel):
    uid: str
    name: str | None = None
    type: str | None = None
    change_fields: list[str] = []


class RelationCompareItem(BaseModel):
    source_uid: str
    target_uid: str
    relation_type: str
    label: str | None = None


class ModelCompareOut(BaseModel):
    base_model: SysMLModelOut
    target_model: SysMLModelOut
    added_elements: list[ModelCompareItem]
    removed_elements: list[ModelCompareItem]
    changed_elements: list[ModelCompareItem]
    added_relations: list[RelationCompareItem]
    removed_relations: list[RelationCompareItem]
