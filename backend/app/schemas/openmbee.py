from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.sysml import SysMLModelOut


class OpenMbeeConfigOut(BaseModel):
    mms_configured: bool
    doc_convert_configured: bool
    mms_url: str | None = None
    doc_convert_url: str | None = None


class OpenMbeeEndpointOut(BaseModel):
    name: str
    method: str
    path: str
    description: str


class OpenMbeeProxyResponse(BaseModel):
    source_url: str
    data: Any


class OpenMbeeSearchParams(BaseModel):
    keyword: str | None = None
    element_type: str | None = None
    limit: int | None = Field(default=None, ge=1, le=500)


class OpenMbeeConvertRequest(BaseModel):
    html: str
    format: Literal["docx", "pdf", "latex"]
    css: str | None = None
    user: str | None = None


class OpenMbeeImportRequest(BaseModel):
    local_project_id: int
    name: str
    description: str | None = None
    mms_project_id: str
    ref_id: str = "master"
    root_element_id: str | None = None
    commit_id: str | None = None
    search_keyword: str | None = None
    element_type: str | None = None
    limit: int = Field(default=200, ge=1, le=2000)
    depth: int | None = Field(default=None, ge=1, le=20)


class OpenMbeeImportResult(BaseModel):
    model: SysMLModelOut
    source_url: str
    imported_elements: int
    imported_relations: int
