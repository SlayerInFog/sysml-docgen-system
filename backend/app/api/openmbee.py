import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.projects import has_project_role
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.project import Project
from app.models.sysml import ModelElement, ModelRelation, SysMLModel
from app.models.user import User
from app.schemas.openmbee import (
    OpenMbeeConfigOut,
    OpenMbeeEndpointOut,
    OpenMbeeImportRequest,
    OpenMbeeImportResult,
    OpenMbeeProxyResponse,
)
from app.services.audit import write_log
from app.services.openmbee_client import (
    OpenMbeeClientError,
    OpenMbeeMmsClient,
    endpoint_catalog,
    extract_mms_elements,
    extract_mms_relations,
    normalize_mms_element,
)
from app.services.versioning import sync_model_branch_head

router = APIRouter(prefix="/openmbee", tags=["OpenMBEE接口适配"])


# 处理 get_client 相关逻辑。
def get_client() -> OpenMbeeMmsClient:
    settings = get_settings()
    return OpenMbeeMmsClient(settings.openmbee_mms_url, settings.openmbee_mms_token)


# 处理 proxy_response 相关逻辑。
def proxy_response(source_url: str, data: Any) -> OpenMbeeProxyResponse:
    return OpenMbeeProxyResponse(source_url=source_url, data=data)


# 处理 translate_openmbee_error 相关逻辑。
def translate_openmbee_error(error: OpenMbeeClientError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=str(error))


# 返回 OpenMBEE 适配配置状态。
@router.get("/config", response_model=OpenMbeeConfigOut)
def openmbee_config(_: User = Depends(get_current_user)) -> OpenMbeeConfigOut:
    settings = get_settings()
    return OpenMbeeConfigOut(
        mms_configured=bool(settings.openmbee_mms_url),
        doc_convert_configured=bool(settings.openmbee_doc_convert_url),
        mms_url=settings.openmbee_mms_url,
        doc_convert_url=settings.openmbee_doc_convert_url,
    )


# 返回保留的 MMS 接口目录。
@router.get("/mms/endpoints", response_model=list[OpenMbeeEndpointOut])
def mms_endpoints(_: User = Depends(get_current_user)) -> list[OpenMbeeEndpointOut]:
    return [OpenMbeeEndpointOut(**endpoint.__dict__) for endpoint in endpoint_catalog()]


# 代理查询 MMS 版本信息。
@router.get("/mms/version", response_model=OpenMbeeProxyResponse)
def mms_version(_: User = Depends(require_roles("admin", "author"))) -> OpenMbeeProxyResponse:
    client = get_client()
    try:
        url = client.require_urls().mms_version()
        return proxy_response(url, client.get(url))
    except OpenMbeeClientError as error:
        raise translate_openmbee_error(error) from error


# 代理查询 MMS 项目列表。
@router.get("/mms/projects", response_model=OpenMbeeProxyResponse)
def mms_projects(
    org_id: str | None = None,
    _: User = Depends(require_roles("admin", "author")),
) -> OpenMbeeProxyResponse:
    client = get_client()
    try:
        url = client.require_urls().projects(org_id)
        return proxy_response(url, client.get(url))
    except OpenMbeeClientError as error:
        raise translate_openmbee_error(error) from error


# 代理查询 MMS 分支列表。
@router.get("/mms/projects/{project_id}/refs", response_model=OpenMbeeProxyResponse)
def mms_refs(project_id: str, _: User = Depends(require_roles("admin", "author"))) -> OpenMbeeProxyResponse:
    client = get_client()
    try:
        url = client.require_urls().refs(project_id)
        return proxy_response(url, client.get(url))
    except OpenMbeeClientError as error:
        raise translate_openmbee_error(error) from error


# 代理读取 MMS 元素数据。
@router.get("/mms/projects/{project_id}/refs/{ref_id}/elements/{element_id}", response_model=OpenMbeeProxyResponse)
def mms_element(
    project_id: str,
    ref_id: str,
    element_id: str,
    commit_id: str | None = None,
    recurse: bool = False,
    depth: int | None = None,
    _: User = Depends(require_roles("admin", "author")),
) -> OpenMbeeProxyResponse:
    client = get_client()
    try:
        urls = client.require_urls()
        url = (
            urls.owned_element(project_id, ref_id, element_id, commit_id, depth)
            if recurse
            else urls.element(project_id, ref_id, element_id, commit_id)
        )
        return proxy_response(url, client.get(url))
    except OpenMbeeClientError as error:
        raise translate_openmbee_error(error) from error


# 代理执行 MMS 搜索。
@router.get("/mms/projects/{project_id}/refs/{ref_id}/search", response_model=OpenMbeeProxyResponse)
def mms_search(
    project_id: str,
    ref_id: str,
    keyword: str | None = None,
    element_type: str | None = None,
    limit: int | None = None,
    _: User = Depends(require_roles("admin", "author")),
) -> OpenMbeeProxyResponse:
    client = get_client()
    try:
        params = {"keyword": keyword, "type": element_type, "limit": limit}
        url = client.require_urls().search(project_id, ref_id, params)
        return proxy_response(url, client.get(url))
    except OpenMbeeClientError as error:
        raise translate_openmbee_error(error) from error


# 将 MMS 数据导入为本地模型版本。
@router.post("/mms/import", response_model=OpenMbeeImportResult, status_code=201)
def import_mms_model(
    payload: OpenMbeeImportRequest,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> OpenMbeeImportResult:
    project = db.query(Project).filter(Project.id == payload.local_project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if not has_project_role(db, project.id, user, {"manager", "editor"}):
        raise HTTPException(status_code=403, detail="权限不足")

    client = get_client()
    try:
        urls = client.require_urls()
        if payload.root_element_id:
            source_url = urls.owned_element(
                payload.mms_project_id,
                payload.ref_id,
                payload.root_element_id,
                payload.commit_id,
                payload.depth,
            )
        else:
            params = {"keyword": payload.search_keyword, "type": payload.element_type, "limit": payload.limit}
            source_url = urls.search(payload.mms_project_id, payload.ref_id, params)
        raw = client.get(source_url)
    except OpenMbeeClientError as error:
        raise translate_openmbee_error(error) from error

    mms_elements = extract_mms_elements(raw)
    if not mms_elements:
        raise HTTPException(status_code=400, detail="MMS 返回数据中未识别到模型元素")

    snapshot_name = f"openmbee_{uuid4().hex}.json"
    snapshot_path = get_settings().upload_path / snapshot_name
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    latest = (
        db.query(SysMLModel)
        .filter(SysMLModel.project_id == payload.local_project_id, SysMLModel.name == payload.name)
        .order_by(SysMLModel.version.desc())
        .first()
    )
    model = SysMLModel(
        project_id=payload.local_project_id,
        name=payload.name,
        description=payload.description,
        source_filename=f"openmbee:{payload.mms_project_id}/{payload.ref_id}",
        stored_path=str(snapshot_path),
        version=(latest.version + 1) if latest else 1,
        branch_name="main",
        version_tag=None,
        uploaded_by=user.id,
        status="parsed",
    )
    db.add(model)
    db.flush()

    seen_uids: set[str] = set()
    for raw_element in mms_elements:
        item = normalize_mms_element(raw_element)
        uid = item["uid"]
        if not uid or uid in seen_uids:
            continue
        seen_uids.add(uid)
        db.add(
            ModelElement(
                model_id=model.id,
                element_uid=uid,
                name=item["name"] or uid,
                type=item["type"] or "Element",
                documentation=item["documentation"],
                parent_uid=item["parent_uid"],
                raw_json=json.dumps(raw_element, ensure_ascii=False),
            )
        )

    relation_count = 0
    for relation in extract_mms_relations(mms_elements):
        if relation["source_uid"] not in seen_uids or relation["target_uid"] not in seen_uids:
            continue
        db.add(
            ModelRelation(
                model_id=model.id,
                source_uid=relation["source_uid"],
                target_uid=relation["target_uid"],
                relation_type=relation["relation_type"] or "relation",
                label=relation["label"],
            )
        )
        relation_count += 1

    sync_model_branch_head(db, model, user)
    db.commit()
    db.refresh(model)
    write_log(db, user, "import_openmbee_model", "model", model.id, model.name)
    return OpenMbeeImportResult(
        model=model,
        source_url=source_url,
        imported_elements=len(seen_uids),
        imported_relations=relation_count,
    )
