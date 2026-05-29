import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.projects import has_project_role
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.document import DocumentTemplate
from app.models.project import Project
from app.models.sysml import ModelElement, ModelRelation, SysMLModel
from app.models.user import User
from app.models.versioning import VersionBranch, VersionRollbackRecord, VersionTag
from app.schemas.versioning import (
    VersionBranchCreate,
    VersionBranchOut,
    VersionBranchUpdate,
    VersionRollbackCreate,
    VersionRollbackRecordOut,
    VersionTagCreate,
    VersionTagOut,
)
from app.services.audit import write_log

router = APIRouter(prefix="/versioning", tags=["版本管理"])
VersionItemType = Literal["model", "template"]


@router.get("/branches", response_model=list[VersionBranchOut])
def list_branches(
    item_type: VersionItemType,
    project_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[VersionBranch]:
    query = db.query(VersionBranch).outerjoin(Project).filter(VersionBranch.item_type == item_type)
    if project_id is not None:
        ensure_project_access(db, project_id, user)
        query = query.filter(VersionBranch.project_id == project_id)
    elif user.role != "admin":
        query = query.filter(or_(VersionBranch.project_id.is_(None), Project.owner_id == user.id))
    return query.order_by(VersionBranch.updated_at.desc()).all()


@router.post("/branches", response_model=VersionBranchOut, status_code=201)
def create_branch(
    payload: VersionBranchCreate,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> VersionBranch:
    item_type = normalize_item_type(payload.item_type)
    project_id = payload.project_id
    branch_name = normalize_branch_name(payload.name)
    source_model = None
    head_model_id = None
    head_template_id = None

    if item_type == "model":
        if project_id is None:
            raise HTTPException(status_code=400, detail="模型分支必须选择项目")
        ensure_project_access(db, project_id, user, write=True)
        if payload.source_model_id:
            model = ensure_model_access(db, payload.source_model_id, user)
            if model.project_id != project_id:
                raise HTTPException(status_code=400, detail="来源模型不属于所选项目")
            source_model = model
    else:
        if project_id is not None:
            ensure_project_access(db, project_id, user, write=True)
        if payload.source_template_id:
            template = ensure_template_access(db, payload.source_template_id, user)
            if template.project_id != project_id:
                raise HTTPException(status_code=400, detail="来源模板不属于所选范围")
            head_template_id = template.id

    ensure_unique_name(db, VersionBranch, item_type, project_id, branch_name, "该范围下已存在同名分支")
    branch = VersionBranch(
        project_id=project_id,
        item_type=item_type,
        name=branch_name,
        description=payload.description,
        head_model_id=head_model_id,
        head_template_id=head_template_id,
        created_by=user.id,
    )
    db.add(branch)
    db.flush()
    if source_model is not None:
        new_model = clone_model_version(db, source_model, user, branch.name, "branch")
        branch.head_model_id = new_model.id
    db.commit()
    db.refresh(branch)
    write_log(db, user, "create_version_branch", f"{item_type}_branch", branch.id, branch.name)
    return branch


@router.patch("/branches/{branch_id}", response_model=VersionBranchOut)
def update_branch(
    branch_id: int,
    payload: VersionBranchUpdate,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> VersionBranch:
    branch = ensure_branch_access(db, branch_id, user, write=True)
    old_name = branch.name
    next_name = normalize_branch_name(payload.name) if payload.name is not None else branch.name
    if next_name != branch.name:
        ensure_unique_name(db, VersionBranch, branch.item_type, branch.project_id, next_name, "该范围下已存在同名分支")
        branch.name = next_name
        if branch.item_type == "model" and branch.project_id is not None:
            (
                db.query(SysMLModel)
                .filter(SysMLModel.project_id == branch.project_id, SysMLModel.branch_name == old_name)
                .update({SysMLModel.branch_name: next_name}, synchronize_session=False)
            )
    if payload.description is not None:
        branch.description = payload.description
    db.commit()
    db.refresh(branch)
    write_log(db, user, "update_version_branch", f"{branch.item_type}_branch", branch.id, branch.name)
    return branch


@router.delete("/branches/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_branch(
    branch_id: int,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> None:
    branch = ensure_branch_access(db, branch_id, user, write=True)
    if branch.head_model_id or branch.head_template_id:
        raise HTTPException(status_code=400, detail="分支仍有当前版本，不能删除")
    if db.query(VersionTag).filter(VersionTag.branch_id == branch.id).first():
        raise HTTPException(status_code=400, detail="分支仍有关联标签，不能删除")
    if db.query(VersionRollbackRecord).filter(VersionRollbackRecord.branch_id == branch.id).first():
        raise HTTPException(status_code=400, detail="分支仍有回滚记录，不能删除")
    if branch.item_type == "model" and branch.project_id is not None:
        has_models = (
            db.query(SysMLModel)
            .filter(SysMLModel.project_id == branch.project_id, SysMLModel.branch_name == branch.name)
            .first()
        )
        if has_models:
            raise HTTPException(status_code=400, detail="分支仍有模型版本，不能删除")
    db.delete(branch)
    db.commit()
    write_log(db, user, "delete_version_branch", f"{branch.item_type}_branch", branch_id, branch.name)


@router.get("/tags", response_model=list[VersionTagOut])
def list_tags(
    item_type: VersionItemType,
    project_id: int | None = None,
    branch_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[VersionTag]:
    query = db.query(VersionTag).outerjoin(Project).filter(VersionTag.item_type == item_type)
    if project_id is not None:
        ensure_project_access(db, project_id, user)
        query = query.filter(VersionTag.project_id == project_id)
    elif user.role != "admin":
        query = query.filter(or_(VersionTag.project_id.is_(None), Project.owner_id == user.id))
    if branch_id is not None:
        branch = ensure_branch_access(db, branch_id, user)
        query = query.filter(VersionTag.branch_id == branch.id)
    return query.order_by(VersionTag.created_at.desc()).all()


@router.post("/tags", response_model=VersionTagOut, status_code=201)
def create_tag(
    payload: VersionTagCreate,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> VersionTag:
    item_type = normalize_item_type(payload.item_type)
    project_id = payload.project_id
    model_id = None
    template_id = None
    snapshot_json = None

    branch = None
    if payload.branch_id:
        branch = ensure_branch_access(db, payload.branch_id, user, write=True)
        if branch.item_type != item_type:
            raise HTTPException(status_code=400, detail="标签类型与分支类型不一致")
        if branch.project_id != project_id:
            raise HTTPException(status_code=400, detail="标签范围与分支范围不一致")

    if item_type == "model":
        if project_id is None or not payload.model_id:
            raise HTTPException(status_code=400, detail="模型标签必须选择项目和模型")
        if branch is None:
            raise HTTPException(status_code=400, detail="模型标签必须选择分支")
        ensure_project_access(db, project_id, user, write=True)
        model = ensure_model_access(db, payload.model_id, user)
        if model.project_id != project_id:
            raise HTTPException(status_code=400, detail="标签目标模型不属于所选项目")
        if branch and model.branch_name != branch.name:
            raise HTTPException(status_code=400, detail="标签目标模型不属于所选分支")
        model_id = model.id
    else:
        if project_id is not None:
            ensure_project_access(db, project_id, user, write=True)
        if not payload.template_id:
            raise HTTPException(status_code=400, detail="模板标签必须选择模板")
        template = ensure_template_access(db, payload.template_id, user)
        if template.project_id != project_id:
            raise HTTPException(status_code=400, detail="标签目标模板不属于所选范围")
        template_id = template.id
        snapshot_json = json.dumps(
            {
                "name": template.name,
                "description": template.description,
                "content": template.content,
                "version": template.version,
                "project_id": template.project_id,
            },
            ensure_ascii=False,
        )

    ensure_unique_name(db, VersionTag, item_type, project_id, payload.name, "该范围下已存在同名标签")
    tag = VersionTag(
        project_id=project_id,
        item_type=item_type,
        branch_id=branch.id if branch else None,
        model_id=model_id,
        template_id=template_id,
        name=payload.name,
        description=payload.description,
        snapshot_json=snapshot_json,
        created_by=user.id,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    write_log(db, user, "create_version_tag", f"{item_type}_tag", tag.id, tag.name)
    return tag


@router.post("/rollback", response_model=VersionRollbackRecordOut, status_code=201)
def rollback(
    payload: VersionRollbackCreate,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> VersionRollbackRecord:
    item_type = normalize_item_type(payload.item_type)
    branch = ensure_branch_access(db, payload.branch_id, user, write=True)
    if branch.item_type != item_type:
        raise HTTPException(status_code=400, detail="回滚类型与分支类型不一致")
    if branch.project_id != payload.project_id:
        raise HTTPException(status_code=400, detail="回滚范围与分支范围不一致")

    tag = None
    target_model = None
    new_model = None
    target_template = None
    new_template = None

    if payload.tag_id:
        tag = ensure_tag_access(db, payload.tag_id, user)
        if tag.item_type != item_type or tag.project_id != payload.project_id:
            raise HTTPException(status_code=400, detail="回滚标签与当前范围不一致")
        if tag.branch_id != branch.id:
            raise HTTPException(status_code=400, detail="回滚标签不属于目标分支")

    if item_type == "model":
        target_model_id = tag.model_id if tag else payload.target_model_id
        if not target_model_id:
            raise HTTPException(status_code=400, detail="请选择回滚目标模型或标签")
        target_model = ensure_model_access(db, target_model_id, user)
        if target_model.project_id != payload.project_id:
            raise HTTPException(status_code=400, detail="回滚目标模型不属于所选项目")
        if target_model.branch_name != branch.name:
            raise HTTPException(status_code=400, detail="回滚目标模型不属于目标分支")
        new_model = clone_model_version(db, target_model, user, branch.name)
        branch.head_model_id = new_model.id
    else:
        target_template_id = tag.template_id if tag else payload.target_template_id
        if not target_template_id:
            raise HTTPException(status_code=400, detail="请选择回滚目标模板或标签")
        target_template = ensure_template_access(db, target_template_id, user)
        if target_template.project_id != payload.project_id:
            raise HTTPException(status_code=400, detail="回滚目标模板不属于所选范围")
        new_template = clone_template_version(db, target_template, user, tag.snapshot_json if tag else None)
        branch.head_template_id = new_template.id

    record = VersionRollbackRecord(
        project_id=payload.project_id,
        item_type=item_type,
        branch_id=branch.id,
        tag_id=tag.id if tag else None,
        target_model_id=target_model.id if target_model else None,
        new_model_id=new_model.id if new_model else None,
        target_template_id=target_template.id if target_template else None,
        new_template_id=new_template.id if new_template else None,
        reason=payload.reason,
        created_by=user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    write_log(db, user, "rollback_version", f"{item_type}_rollback", record.id, payload.reason)
    return record


@router.get("/rollback-records", response_model=list[VersionRollbackRecordOut])
def list_rollback_records(
    item_type: VersionItemType,
    project_id: int | None = None,
    branch_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[VersionRollbackRecord]:
    query = db.query(VersionRollbackRecord).outerjoin(Project).filter(VersionRollbackRecord.item_type == item_type)
    if project_id is not None:
        ensure_project_access(db, project_id, user)
        query = query.filter(VersionRollbackRecord.project_id == project_id)
    elif user.role != "admin":
        query = query.filter(or_(VersionRollbackRecord.project_id.is_(None), Project.owner_id == user.id))
    if branch_id is not None:
        branch = ensure_branch_access(db, branch_id, user)
        query = query.filter(VersionRollbackRecord.branch_id == branch.id)
    return query.order_by(VersionRollbackRecord.created_at.desc()).all()


def clone_model_version(
    db: Session,
    target_model: SysMLModel,
    user: User,
    branch_name: str,
    status: str = "rollback",
) -> SysMLModel:
    target_branch = (branch_name or "main").strip() or "main"
    latest = (
        db.query(SysMLModel)
        .filter(
            SysMLModel.project_id == target_model.project_id,
            SysMLModel.name == target_model.name,
            SysMLModel.branch_name == target_branch,
        )
        .order_by(SysMLModel.version.desc())
        .first()
    )
    new_model = SysMLModel(
        project_id=target_model.project_id,
        name=target_model.name,
        description=target_model.description,
        source_filename=f"rollback-{target_model.source_filename}"[:255],
        stored_path=target_model.stored_path,
        version=(latest.version + 1) if latest else 1,
        branch_name=target_branch,
        version_tag=None,
        uploaded_by=user.id,
        status=status,
    )
    db.add(new_model)
    db.flush()

    for element in db.query(ModelElement).filter(ModelElement.model_id == target_model.id).all():
        db.add(
            ModelElement(
                model_id=new_model.id,
                element_uid=element.element_uid,
                name=element.name,
                type=element.type,
                documentation=element.documentation,
                parent_uid=element.parent_uid,
                raw_json=element.raw_json,
            )
        )
    for relation in db.query(ModelRelation).filter(ModelRelation.model_id == target_model.id).all():
        db.add(
            ModelRelation(
                model_id=new_model.id,
                source_uid=relation.source_uid,
                target_uid=relation.target_uid,
                relation_type=relation.relation_type,
                label=relation.label,
            )
        )
    db.flush()
    return new_model


def clone_template_version(
    db: Session,
    target_template: DocumentTemplate,
    user: User,
    snapshot_json: str | None = None,
) -> DocumentTemplate:
    snapshot = json.loads(snapshot_json) if snapshot_json else {}
    name = snapshot.get("name") or target_template.name
    project_id = snapshot.get("project_id", target_template.project_id)
    latest = (
        db.query(DocumentTemplate)
        .filter(DocumentTemplate.project_id == project_id, DocumentTemplate.name == name)
        .order_by(DocumentTemplate.version.desc())
        .first()
    )
    new_template = DocumentTemplate(
        project_id=project_id,
        name=name,
        description=snapshot.get("description", target_template.description),
        content=snapshot.get("content", target_template.content),
        version=(latest.version + 1) if latest else target_template.version + 1,
        branch_name=getattr(target_template, "branch_name", "main") or "main",
        version_tag=None,
    )
    db.add(new_template)
    db.flush()
    return new_template


def normalize_item_type(item_type: str) -> VersionItemType:
    if item_type not in {"model", "template"}:
        raise HTTPException(status_code=400, detail="版本对象类型只支持 model 或 template")
    return item_type  # type: ignore[return-value]


def normalize_branch_name(name: str | None) -> str:
    normalized = (name or "").strip()[:120]
    if not normalized:
        raise HTTPException(status_code=400, detail="分支名称不能为空")
    return normalized


def ensure_unique_name(
    db: Session,
    model_cls,
    item_type: str,
    project_id: int | None,
    name: str,
    message: str,
) -> None:
    exists = (
        db.query(model_cls)
        .filter(model_cls.item_type == item_type, model_cls.project_id == project_id, model_cls.name == name)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail=message)


def ensure_project_access(db: Session, project_id: int, user: User, write: bool = False) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    roles = {"manager", "editor"} if write else None
    if not has_project_role(db, project.id, user, roles):
        raise HTTPException(status_code=403, detail="权限不足")
    return project


def ensure_model_access(db: Session, model_id: int, user: User) -> SysMLModel:
    model = db.query(SysMLModel).join(Project).filter(SysMLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    if not has_project_role(db, model.project_id, user):
        raise HTTPException(status_code=403, detail="权限不足")
    return model


def ensure_template_access(db: Session, template_id: int, user: User) -> DocumentTemplate:
    template = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    if template.project_id is not None and not has_project_role(db, template.project_id, user):
        raise HTTPException(status_code=403, detail="权限不足")
    return template


def ensure_branch_access(db: Session, branch_id: int, user: User, write: bool = False) -> VersionBranch:
    branch = db.query(VersionBranch).outerjoin(Project).filter(VersionBranch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="分支不存在")
    if branch.project_id is not None:
        ensure_project_access(db, branch.project_id, user, write=write)
    return branch


def ensure_tag_access(db: Session, tag_id: int, user: User) -> VersionTag:
    tag = db.query(VersionTag).outerjoin(Project).filter(VersionTag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    if tag.project_id is not None:
        ensure_project_access(db, tag.project_id, user)
    return tag
