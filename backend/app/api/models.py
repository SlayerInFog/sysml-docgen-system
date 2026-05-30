import json
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.api.projects import has_project_role
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.document import GeneratedDocument
from app.models.project import Project, ProjectMember
from app.models.sysml import ModelElement, ModelRelation, SysMLModel
from app.models.user import User
from app.schemas.sysml import (
    ModelCompareItem,
    ModelCompareOut,
    ModelElementOut,
    ModelElementUpdate,
    ModelGraphOut,
    ModelRelationCreate,
    ModelRelationOut,
    ModelRelationUpdate,
    RelationCompareItem,
    SysMLModelOut,
    SysMLModelUpdate,
)
from app.services.audit import write_log
from app.services.sysml_parser import parse_model_file
from app.services.versioning import reassign_model_branch_heads_before_delete, sync_model_branch_head

router = APIRouter(prefix="/models", tags=["模型管理"])
settings = get_settings()


# 上传模型文件并解析为元素和关系。
@router.post("/upload", response_model=SysMLModelOut, status_code=201)
def upload_model(
    project_id: int = Form(...),
    name: str = Form(...),
    description: str | None = Form(None),
    branch_name: str = Form("main"),
    version_tag: str | None = Form(None),
    file: UploadFile = File(...),
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> SysMLModel:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if not has_project_role(db, project.id, user, {"manager", "editor"}):
        raise HTTPException(status_code=403, detail="权限不足")

    normalized_branch = _normalize_branch(branch_name)
    normalized_tag = _normalize_tag(version_tag)
    if normalized_tag and _model_tag_exists(db, project_id, name, normalized_tag):
        raise HTTPException(status_code=400, detail="Version tag already exists for this model")

    suffix = Path(file.filename or "model.xmi").suffix or ".xmi"
    stored_name = f"{uuid4().hex}{suffix}"
    upload_dir = settings.upload_path
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = upload_dir / stored_name
    with stored_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    parsed = parse_model_file(stored_path)
    if not parsed.elements:
        raise HTTPException(status_code=400, detail="未解析到模型元素，请检查文件格式")

    latest = (
        db.query(SysMLModel)
        .filter(
            SysMLModel.project_id == project_id,
            SysMLModel.name == name,
            SysMLModel.branch_name == normalized_branch,
        )
        .order_by(SysMLModel.version.desc())
        .first()
    )
    model = SysMLModel(
        project_id=project_id,
        name=name,
        description=description,
        source_filename=file.filename or stored_name,
        stored_path=str(stored_path),
        version=(latest.version + 1) if latest else 1,
        branch_name=normalized_branch,
        version_tag=normalized_tag,
        uploaded_by=user.id,
        status="parsed",
    )
    db.add(model)
    db.flush()

    for element in parsed.elements:
        db.add(
            ModelElement(
                model_id=model.id,
                element_uid=element.uid,
                name=element.name[:255],
                type=element.type[:80],
                documentation=element.documentation,
                parent_uid=element.parent_uid,
                raw_json=json.dumps(element.raw, ensure_ascii=False),
            )
        )
    for relation in parsed.relations:
        db.add(
            ModelRelation(
                model_id=model.id,
                source_uid=relation.source_uid,
                target_uid=relation.target_uid,
                relation_type=relation.relation_type[:80],
                label=relation.label,
            )
        )

    sync_model_branch_head(db, model, user)
    db.commit()
    db.refresh(model)
    write_log(db, user, "upload_model", "model", model.id, f"解析元素 {len(parsed.elements)} 个")
    return model


# 按权限和项目筛选模型列表。
@router.get("", response_model=list[SysMLModelOut])
def list_models(project_id: int | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(SysMLModel).join(Project)
    if project_id:
        query = query.filter(SysMLModel.project_id == project_id)
    if user.role != "admin":
        query = query.outerjoin(ProjectMember).filter(
            (Project.owner_id == user.id) | (ProjectMember.user_id == user.id)
        )
    return query.order_by(SysMLModel.created_at.desc()).all()


# 编辑模型信息并生成新版本。
@router.patch("/{model_id}", response_model=SysMLModelOut)
def update_model(
    model_id: int,
    payload: SysMLModelUpdate,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> SysMLModel:
    model = ensure_model_access(db, model_id, user)
    if not has_project_role(db, model.project_id, user, {"manager", "editor"}):
        raise HTTPException(status_code=403, detail="权限不足")

    next_name = payload.name[:160] if payload.name is not None else model.name
    next_description = payload.description if payload.description is not None else model.description
    if next_name == model.name and next_description == model.description:
        return model

    new_model = _clone_model_for_update(db, model, user, status="edited")
    new_model.name = next_name
    new_model.description = next_description
    sync_model_branch_head(db, new_model, user)

    db.commit()
    db.refresh(new_model)
    write_log(db, user, "update_model", "model", new_model.id, f"from:{model.id}")
    return new_model


# 删除模型及相关解析数据。
@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(
    model_id: int,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> None:
    model = ensure_model_access(db, model_id, user)
    if not has_project_role(db, model.project_id, user, {"manager", "editor"}):
        raise HTTPException(status_code=403, detail="权限不足")

    used_count = db.query(GeneratedDocument).filter(GeneratedDocument.model_id == model.id).count()
    if used_count:
        raise HTTPException(status_code=400, detail="Model has generated documents and cannot be deleted")

    stored_path = Path(model.stored_path) if model.stored_path else None
    model_name = model.name
    reassign_model_branch_heads_before_delete(db, model)
    _delete_model_versioning_records(db, model.id)
    db.delete(model)
    db.commit()

    if stored_path and stored_path.exists() and _can_remove_model_file(db, model):
        try:
            stored_path.unlink()
        except OSError:
            pass

    write_log(db, user, "delete_model", "model", model_id, model_name)


# 对比两个模型版本的元素和关系差异。
@router.get("/compare", response_model=ModelCompareOut)
def compare_models(
    base_model_id: int,
    target_model_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ModelCompareOut:
    base_model = ensure_model_access(db, base_model_id, user)
    target_model = ensure_model_access(db, target_model_id, user)
    if base_model.project_id != target_model.project_id:
        raise HTTPException(status_code=400, detail="只能对比同一项目下的模型版本")

    base_elements = {
        item.element_uid: item for item in db.query(ModelElement).filter(ModelElement.model_id == base_model_id).all()
    }
    target_elements = {
        item.element_uid: item for item in db.query(ModelElement).filter(ModelElement.model_id == target_model_id).all()
    }
    base_uids = set(base_elements)
    target_uids = set(target_elements)

    added_elements = [_element_compare_item(target_elements[uid]) for uid in sorted(target_uids - base_uids)]
    removed_elements = [_element_compare_item(base_elements[uid]) for uid in sorted(base_uids - target_uids)]
    changed_elements: list[ModelCompareItem] = []
    for uid in sorted(base_uids & target_uids):
        base = base_elements[uid]
        target = target_elements[uid]
        changed_fields = [
            field
            for field in ("name", "type", "documentation", "parent_uid")
            if getattr(base, field) != getattr(target, field)
        ]
        if changed_fields:
            changed_elements.append(_element_compare_item(target, changed_fields))

    base_relations = {
        (item.source_uid, item.target_uid, item.relation_type, item.label or "")
        for item in db.query(ModelRelation).filter(ModelRelation.model_id == base_model_id).all()
    }
    target_relations = {
        (item.source_uid, item.target_uid, item.relation_type, item.label or "")
        for item in db.query(ModelRelation).filter(ModelRelation.model_id == target_model_id).all()
    }

    return ModelCompareOut(
        base_model=SysMLModelOut.model_validate(base_model),
        target_model=SysMLModelOut.model_validate(target_model),
        added_elements=added_elements[:200],
        removed_elements=removed_elements[:200],
        changed_elements=changed_elements[:200],
        added_relations=[_relation_compare_item(item) for item in sorted(target_relations - base_relations)[:200]],
        removed_relations=[_relation_compare_item(item) for item in sorted(base_relations - target_relations)[:200]],
    )


# 读取模型元素列表。
@router.get("/{model_id}/elements", response_model=list[ModelElementOut])
def list_elements(model_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_model_access(db, model_id, user)
    return db.query(ModelElement).filter(ModelElement.model_id == model_id).order_by(ModelElement.type, ModelElement.name).all()


# 读取模型图视图所需的元素和关系。
@router.get("/{model_id}/graph", response_model=ModelGraphOut)
def graph(model_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_model_access(db, model_id, user)
    elements = db.query(ModelElement).filter(ModelElement.model_id == model_id).all()
    relations = db.query(ModelRelation).filter(ModelRelation.model_id == model_id).all()
    return ModelGraphOut(
        elements=[ModelElementOut.model_validate(item) for item in elements],
        relations=[ModelRelationOut.model_validate(item) for item in relations],
    )


# 轻量编辑模型元素并生成新版本。
@router.patch("/elements/{element_id}", response_model=ModelElementOut)
def update_element(
    element_id: int,
    payload: ModelElementUpdate,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
):
    element = db.query(ModelElement).filter(ModelElement.id == element_id).first()
    if not element:
        raise HTTPException(status_code=404, detail="模型元素不存在")

    model = ensure_model_access(db, element.model_id, user)
    if not has_project_role(db, model.project_id, user, {"manager", "editor"}):
        raise HTTPException(status_code=403, detail="权限不足")

    next_name = payload.name[:255] if payload.name is not None else element.name
    next_documentation = payload.documentation if payload.documentation is not None else element.documentation
    if next_name == element.name and next_documentation == element.documentation:
        return element

    new_model = _clone_model_for_update(db, model, user, status="edited")
    new_element = (
        db.query(ModelElement)
        .filter(ModelElement.model_id == new_model.id, ModelElement.element_uid == element.element_uid)
        .first()
    )
    if not new_element:
        raise HTTPException(status_code=500, detail="创建元素编辑版本失败")

    new_element.name = next_name
    new_element.documentation = next_documentation
    sync_model_branch_head(db, new_model, user)

    db.commit()
    db.refresh(new_element)
    write_log(db, user, "update_element", "element", new_element.id, f"from:{element.id}")
    return new_element


# 新增模型关系并生成新版本。
@router.post("/{model_id}/relations", response_model=ModelRelationOut, status_code=201)
def create_relation(
    model_id: int,
    payload: ModelRelationCreate,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> ModelRelation:
    model = ensure_model_access(db, model_id, user)
    _ensure_model_edit_access(db, model, user)
    source_uid = _normalize_relation_uid(payload.source_uid, "源元素不能为空")
    target_uid = _normalize_relation_uid(payload.target_uid, "目标元素不能为空")
    relation_type = _normalize_relation_type(payload.relation_type)
    _ensure_relation_endpoint_exists(db, model.id, source_uid, "源元素不存在")
    _ensure_relation_endpoint_exists(db, model.id, target_uid, "目标元素不存在")

    new_model = _clone_model_for_update(db, model, user, status="edited")
    new_relation = ModelRelation(
        model_id=new_model.id,
        source_uid=source_uid,
        target_uid=target_uid,
        relation_type=relation_type,
        label=_normalize_relation_label(payload.label),
    )
    db.add(new_relation)
    sync_model_branch_head(db, new_model, user)

    db.commit()
    db.refresh(new_relation)
    write_log(db, user, "create_relation", "relation", new_relation.id, f"from_model:{model.id}")
    return new_relation


# 修改模型关系并生成新版本。
@router.patch("/relations/{relation_id}", response_model=ModelRelationOut)
def update_relation(
    relation_id: int,
    payload: ModelRelationUpdate,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> ModelRelation:
    relation = db.query(ModelRelation).filter(ModelRelation.id == relation_id).first()
    if not relation:
        raise HTTPException(status_code=404, detail="模型关系不存在")

    model = ensure_model_access(db, relation.model_id, user)
    _ensure_model_edit_access(db, model, user)
    next_source_uid = _normalize_relation_uid(payload.source_uid, "源元素不能为空") if payload.source_uid is not None else relation.source_uid
    next_target_uid = _normalize_relation_uid(payload.target_uid, "目标元素不能为空") if payload.target_uid is not None else relation.target_uid
    next_relation_type = _normalize_relation_type(payload.relation_type) if payload.relation_type is not None else relation.relation_type
    next_label = _normalize_relation_label(payload.label) if "label" in payload.model_fields_set else relation.label

    if (
        next_source_uid == relation.source_uid
        and next_target_uid == relation.target_uid
        and next_relation_type == relation.relation_type
        and next_label == relation.label
    ):
        return relation

    _ensure_relation_endpoint_exists(db, model.id, next_source_uid, "源元素不存在")
    _ensure_relation_endpoint_exists(db, model.id, next_target_uid, "目标元素不存在")

    new_model = _clone_model_for_update(db, model, user, status="edited")
    new_relation = (
        db.query(ModelRelation)
        .filter(
            ModelRelation.model_id == new_model.id,
            ModelRelation.source_uid == relation.source_uid,
            ModelRelation.target_uid == relation.target_uid,
            ModelRelation.relation_type == relation.relation_type,
            ModelRelation.label == relation.label,
        )
        .first()
    )
    if not new_relation:
        raise HTTPException(status_code=500, detail="创建关系编辑版本失败")

    new_relation.source_uid = next_source_uid
    new_relation.target_uid = next_target_uid
    new_relation.relation_type = next_relation_type
    new_relation.label = next_label
    sync_model_branch_head(db, new_model, user)

    db.commit()
    db.refresh(new_relation)
    write_log(db, user, "update_relation", "relation", new_relation.id, f"from:{relation.id}")
    return new_relation


# 删除模型关系并生成新版本。
@router.delete("/relations/{relation_id}", response_model=SysMLModelOut)
def delete_relation(
    relation_id: int,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> SysMLModel:
    relation = db.query(ModelRelation).filter(ModelRelation.id == relation_id).first()
    if not relation:
        raise HTTPException(status_code=404, detail="模型关系不存在")

    model = ensure_model_access(db, relation.model_id, user)
    _ensure_model_edit_access(db, model, user)
    new_model = _clone_model_for_update(db, model, user, status="edited")
    new_relation = (
        db.query(ModelRelation)
        .filter(
            ModelRelation.model_id == new_model.id,
            ModelRelation.source_uid == relation.source_uid,
            ModelRelation.target_uid == relation.target_uid,
            ModelRelation.relation_type == relation.relation_type,
            ModelRelation.label == relation.label,
        )
        .first()
    )
    if new_relation:
        db.delete(new_relation)
    sync_model_branch_head(db, new_model, user)

    db.commit()
    db.refresh(new_model)
    write_log(db, user, "delete_relation", "relation", relation_id, f"new_model:{new_model.id}")
    return new_model


# 处理 ensure_model_access 相关逻辑。
def ensure_model_access(db: Session, model_id: int, user: User) -> SysMLModel:
    model = db.query(SysMLModel).join(Project).filter(SysMLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    if not has_project_role(db, model.project_id, user):
        raise HTTPException(status_code=403, detail="权限不足")
    return model


# 处理 _ensure_model_edit_access 相关逻辑。
def _ensure_model_edit_access(db: Session, model: SysMLModel, user: User) -> None:
    if not has_project_role(db, model.project_id, user, {"manager", "editor"}):
        raise HTTPException(status_code=403, detail="权限不足")


# 处理 _ensure_relation_endpoint_exists 相关逻辑。
def _ensure_relation_endpoint_exists(db: Session, model_id: int, element_uid: str, detail: str) -> None:
    exists = db.query(ModelElement.id).filter(ModelElement.model_id == model_id, ModelElement.element_uid == element_uid).first()
    if not exists:
        raise HTTPException(status_code=400, detail=detail)


# 处理 _normalize_relation_uid 相关逻辑。
def _normalize_relation_uid(value: str, empty_detail: str) -> str:
    uid = value.strip()
    if not uid:
        raise HTTPException(status_code=400, detail=empty_detail)
    return uid[:255]


# 处理 _normalize_relation_type 相关逻辑。
def _normalize_relation_type(value: str) -> str:
    relation_type = value.strip()
    if not relation_type:
        raise HTTPException(status_code=400, detail="关系类型不能为空")
    return relation_type[:80]


# 处理 _normalize_relation_label 相关逻辑。
def _normalize_relation_label(value: str | None) -> str | None:
    label = (value or "").strip()
    return label or None


# 处理 _element_compare_item 相关逻辑。
def _element_compare_item(element: ModelElement, change_fields: list[str] | None = None) -> ModelCompareItem:
    return ModelCompareItem(
        uid=element.element_uid,
        name=element.name,
        type=element.type,
        change_fields=change_fields or [],
    )


# 处理 _relation_compare_item 相关逻辑。
def _relation_compare_item(relation: tuple[str, str, str, str]) -> RelationCompareItem:
    source_uid, target_uid, relation_type, label = relation
    return RelationCompareItem(
        source_uid=source_uid,
        target_uid=target_uid,
        relation_type=relation_type,
        label=label or None,
    )


# 处理 _normalize_branch 相关逻辑。
def _normalize_branch(value: str | None) -> str:
    branch = (value or "main").strip()
    return branch[:80] or "main"


# 处理 _normalize_tag 相关逻辑。
def _normalize_tag(value: str | None) -> str | None:
    tag = (value or "").strip()
    return tag[:80] or None


# 处理 _model_tag_exists 相关逻辑。
def _model_tag_exists(db: Session, project_id: int, name: str, tag: str) -> bool:
    return bool(
        db.query(SysMLModel)
        .filter(SysMLModel.project_id == project_id, SysMLModel.name == name, SysMLModel.version_tag == tag)
        .first()
    )


# 处理 _delete_model_versioning_records 相关逻辑。
def _delete_model_versioning_records(db: Session, model_id: int) -> None:
    bind = db.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())
    if "version_rollback_records" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("version_rollback_records")}
        reference_columns = [column for column in ("target_model_id", "new_model_id", "model_id") if column in columns]
        if "tag_id" in columns and "version_tags" in table_names:
            reference_columns.append("tag_id")
        if reference_columns:
            conditions = []
            for column in reference_columns:
                if column == "tag_id":
                    conditions.append("tag_id IN (SELECT id FROM version_tags WHERE model_id = :model_id)")
                else:
                    conditions.append(f"{column} = :model_id")
            db.execute(
                text(f"DELETE FROM version_rollback_records WHERE {' OR '.join(conditions)}"),
                {"model_id": model_id},
            )
    if "version_tags" in table_names:
        db.execute(
            text("DELETE FROM version_tags WHERE model_id = :model_id"),
            {"model_id": model_id},
        )


# 处理 _can_remove_model_file 相关逻辑。
def _can_remove_model_file(db: Session, model: SysMLModel) -> bool:
    if not model.stored_path:
        return False
    sibling = (
        db.query(SysMLModel.id)
        .filter(SysMLModel.stored_path == model.stored_path, SysMLModel.id != model.id)
        .first()
    )
    return sibling is None


# 处理 _clone_model_for_update 相关逻辑。
def _clone_model_for_update(db: Session, source_model: SysMLModel, user: User, status: str) -> SysMLModel:
    latest = (
        db.query(SysMLModel)
        .filter(
            SysMLModel.project_id == source_model.project_id,
            SysMLModel.name == source_model.name,
            SysMLModel.branch_name == source_model.branch_name,
        )
        .order_by(SysMLModel.version.desc())
        .first()
    )
    new_model = SysMLModel(
        project_id=source_model.project_id,
        name=source_model.name,
        description=source_model.description,
        source_filename=f"{status}-{source_model.source_filename}"[:255],
        stored_path=source_model.stored_path,
        version=(latest.version + 1) if latest else source_model.version + 1,
        branch_name=source_model.branch_name,
        version_tag=None,
        uploaded_by=user.id,
        status=status,
    )
    db.add(new_model)
    db.flush()

    for source_element in db.query(ModelElement).filter(ModelElement.model_id == source_model.id).all():
        db.add(
            ModelElement(
                model_id=new_model.id,
                element_uid=source_element.element_uid,
                name=source_element.name,
                type=source_element.type,
                documentation=source_element.documentation,
                parent_uid=source_element.parent_uid,
                raw_json=source_element.raw_json,
            )
        )
    for source_relation in db.query(ModelRelation).filter(ModelRelation.model_id == source_model.id).all():
        db.add(
            ModelRelation(
                model_id=new_model.id,
                source_uid=source_relation.source_uid,
                target_uid=source_relation.target_uid,
                relation_type=source_relation.relation_type,
                label=source_relation.label,
            )
        )

    db.flush()
    return new_model
