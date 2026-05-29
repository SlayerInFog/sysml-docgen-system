from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from jinja2 import Template
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.api.projects import has_project_role
from app.models.document import DocumentTemplate, DocumentTemplateVersion, GeneratedDocument
from app.models.project import Project, ProjectMember
from app.models.sysml import SysMLModel
from app.models.user import User
from app.schemas.document import (
    GenerateDocumentRequest,
    GeneratedDocumentOut,
    TemplateCreate,
    TemplateOut,
    TemplatePreviewRequest,
    TemplateUpdate,
    TemplateVersionOut,
)
from app.services.audit import write_log
from app.services.document_generator import (
    DEFAULT_TEMPLATE,
    export_model_docx_summary,
    export_model_pdf_summary,
    render_document_html,
)

router = APIRouter(prefix="/documents", tags=["文档生成"])
settings = get_settings()


@router.post("/templates", response_model=TemplateOut, status_code=201)
def create_template(
    payload: TemplateCreate,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> DocumentTemplate:
    if payload.project_id:
        project = db.query(Project).filter(Project.id == payload.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        if not has_project_role(db, project.id, user, {"manager", "editor"}):
            raise HTTPException(status_code=403, detail="权限不足")
    branch_name = _normalize_branch(payload.branch_name)
    version_tag = _normalize_tag(payload.version_tag)
    if version_tag and _template_tag_exists(db, payload.project_id, payload.name, version_tag):
        raise HTTPException(status_code=400, detail="Version tag already exists for this template")
    template = DocumentTemplate(
        project_id=payload.project_id,
        name=payload.name,
        description=payload.description,
        content=payload.content,
        branch_name=branch_name,
        version_tag=version_tag,
    )
    db.add(template)
    db.flush()
    _save_template_version(db, template, user)
    db.commit()
    db.refresh(template)
    write_log(db, user, "create_template", "template", template.id, template.name)
    return template


@router.get("/templates", response_model=list[TemplateOut])
def list_templates(project_id: int | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(DocumentTemplate)
    if project_id:
        query = query.filter((DocumentTemplate.project_id == project_id) | (DocumentTemplate.project_id.is_(None)))
    return query.order_by(DocumentTemplate.project_id.isnot(None).desc(), DocumentTemplate.created_at.desc()).all()


@router.patch("/templates/{template_id}", response_model=TemplateOut)
def update_template(
    template_id: int,
    payload: TemplateUpdate,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> DocumentTemplate:
    template = _get_template_for_write(db, template_id, user)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    changed_content = payload.content is not None and payload.content != template.content
    changed_metadata = (
        (payload.name is not None and payload.name != template.name)
        or (payload.description is not None and payload.description != template.description)
        or (payload.branch_name is not None and _normalize_branch(payload.branch_name) != template.branch_name)
        or (payload.version_tag is not None and _normalize_tag(payload.version_tag) != template.version_tag)
    )
    next_name = payload.name if payload.name is not None else template.name
    next_tag = _normalize_tag(payload.version_tag) if payload.version_tag is not None else template.version_tag
    if next_tag and _template_tag_exists(db, template.project_id, next_name, next_tag, template.id):
        raise HTTPException(status_code=400, detail="Version tag already exists for this template")
    next_version = template.version
    if changed_content or changed_metadata:
        next_version = template.version + 1
    if payload.name is not None:
        template.name = payload.name
    if payload.description is not None:
        template.description = payload.description
    if payload.content is not None:
        template.content = payload.content
    if payload.branch_name is not None:
        template.branch_name = _normalize_branch(payload.branch_name)
    if payload.version_tag is not None:
        template.version_tag = _normalize_tag(payload.version_tag)
    if changed_content or changed_metadata:
        template.version = next_version
        _save_template_version(db, template, user)
    db.commit()
    db.refresh(template)
    write_log(db, user, "update_template", "template", template.id, template.name)
    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> None:
    template = _get_template_for_write(db, template_id, user)
    used_count = db.query(GeneratedDocument).filter(GeneratedDocument.template_id == template_id).count()
    if used_count:
        raise HTTPException(status_code=400, detail="模板已被生成文档引用，不能删除")
    template_name = template.name
    _delete_template_rollback_records(db, template_id)
    db.delete(template)
    db.commit()
    write_log(db, user, "delete_template", "template", template_id, template_name)


@router.get("/templates/{template_id}/versions", response_model=list[TemplateVersionOut])
def list_template_versions(
    template_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentTemplateVersion]:
    template = _get_template_for_read(db, template_id, user)
    return (
        db.query(DocumentTemplateVersion)
        .filter(DocumentTemplateVersion.template_id == template.id)
        .order_by(DocumentTemplateVersion.version.desc())
        .all()
    )


@router.post("/templates/{template_id}/rollback/{version_id}", response_model=TemplateOut)
def rollback_template(
    template_id: int,
    version_id: int,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> DocumentTemplate:
    template = _get_template_for_write(db, template_id, user)
    version = (
        db.query(DocumentTemplateVersion)
        .filter(DocumentTemplateVersion.id == version_id, DocumentTemplateVersion.template_id == template.id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Template version not found")
    template.name = version.name
    template.description = version.description
    template.content = version.content
    template.branch_name = version.branch_name
    template.version_tag = None
    template.version += 1
    _save_template_version(db, template, user)
    db.commit()
    db.refresh(template)
    write_log(db, user, "rollback_template", "template", template.id, f"rollback_to:{version.version}")
    return template


@router.post("/templates/preview")
def preview_template(
    payload: TemplatePreviewRequest,
    _: User = Depends(get_current_user),
) -> dict[str, str]:
    sample_model = {
        "name": "示例 SysML 模型",
        "version": 1,
        "description": "用于模板预览的示例模型",
    }
    sample_elements = [
        {"name": "飞控系统", "type": "Block", "documentation": "无人机飞行控制核心模块"},
        {"name": "导航需求", "type": "Requirement", "documentation": "系统应支持自主航线导航"},
        {"name": "传感器接口", "type": "InterfaceBlock", "documentation": "对接 GPS、IMU 等传感器数据"},
    ]
    sample_relations = [
        {"source_uid": "REQ-001", "target_uid": "BLK-001", "relation_type": "satisfy", "label": "满足"},
        {"source_uid": "BLK-001", "target_uid": "IF-001", "relation_type": "use", "label": "使用"},
    ]
    element_names = {
        "REQ-001": "导航需求",
        "BLK-001": "飞控系统",
        "IF-001": "传感器接口",
    }
    html = Template(payload.content).render(
        title=payload.title,
        model=sample_model,
        elements=sample_elements,
        relations=sample_relations,
        element_names=element_names,
        stats={
            "total_elements": len(sample_elements),
            "total_relations": len(sample_relations),
            "top_types": "Block(1)、Requirement(1)、InterfaceBlock(1)",
        },
    )
    return {"html": html}


@router.post("/generate", response_model=GeneratedDocumentOut, status_code=201)
def generate_document(
    payload: GenerateDocumentRequest,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> GeneratedDocument:
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    model = db.query(SysMLModel).filter(SysMLModel.id == payload.model_id, SysMLModel.project_id == payload.project_id).first()
    template = db.query(DocumentTemplate).filter(DocumentTemplate.id == payload.template_id).first()
    if not project or not model or not template:
        raise HTTPException(status_code=404, detail="项目、模型或模板不存在")
    if not has_project_role(db, project.id, user, {"manager", "editor"}):
        raise HTTPException(status_code=403, detail="权限不足")

    html = render_document_html(db, model, payload.title, template.content)
    out_dir = settings.generated_path
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"document_{payload.project_id}_{payload.model_id}.html"
    html_path.write_text(html, encoding="utf-8")
    doc = GeneratedDocument(
        project_id=payload.project_id,
        model_id=payload.model_id,
        template_id=payload.template_id,
        title=payload.title,
        html_content=html,
        file_path=str(html_path),
        created_by=user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    write_log(db, user, "generate_document", "document", doc.id, doc.title)
    return doc


@router.get("", response_model=list[GeneratedDocumentOut])
def list_generated(project_id: int | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(GeneratedDocument).join(Project)
    if project_id:
        query = query.filter(GeneratedDocument.project_id == project_id)
    if user.role != "admin":
        query = query.outerjoin(ProjectMember).filter(
            (Project.owner_id == user.id) | (ProjectMember.user_id == user.id)
        )
    return query.order_by(GeneratedDocument.created_at.desc()).all()


@router.get("/{document_id}", response_model=GeneratedDocumentOut)
def get_generated(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(GeneratedDocument).join(Project).filter(GeneratedDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    if not has_project_role(db, doc.project_id, user):
        raise HTTPException(status_code=403, detail="权限不足")
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_generated(document_id: int, user: User = Depends(require_roles("admin", "author")), db: Session = Depends(get_db)) -> None:
    doc = get_generated(document_id, user, db)
    if not has_project_role(db, doc.project_id, user, {"manager", "editor"}):
        raise HTTPException(status_code=403, detail="Permission denied")
    file_path = Path(doc.file_path) if doc.file_path else None
    doc_title = doc.title
    db.delete(doc)
    db.commit()
    if file_path and file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            pass
    write_log(db, user, "delete_document", "document", document_id, doc_title)


@router.get("/{document_id}/export/{fmt}")
def export_document(document_id: int, fmt: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = get_generated(document_id, user, db)
    fmt = fmt.lower()
    out_dir = settings.generated_path
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_title = "".join(ch if ch.isalnum() else "_" for ch in doc.title)[:80]
    if fmt == "html":
        path = Path(doc.file_path) if doc.file_path else out_dir / f"{safe_title}.html"
        path.write_text(doc.html_content, encoding="utf-8")
        return FileResponse(path, filename=f"{safe_title}.html", media_type="text/html")
    if fmt == "docx":
        path = out_dir / f"{safe_title}.docx"
        export_model_docx_summary(db, doc, path)
        return FileResponse(path, filename=path.name, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    if fmt == "pdf":
        path = out_dir / f"{safe_title}.pdf"
        export_model_pdf_summary(db, doc, path)
        return FileResponse(path, filename=path.name, media_type="application/pdf")
    raise HTTPException(status_code=400, detail="导出格式只支持 html、docx、pdf")


@router.post("/templates/default", response_model=TemplateOut, status_code=201)
def create_default_template(
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> DocumentTemplate:
    template = DocumentTemplate(
        project_id=None,
        name="默认 SysML 工程文档模板",
        description="参考 OpenMBEE DocGen 思路的轻量 HTML 模板",
        content=DEFAULT_TEMPLATE,
        branch_name="main",
        version_tag="default",
    )
    db.add(template)
    db.flush()
    _save_template_version(db, template, user)
    db.commit()
    db.refresh(template)
    write_log(db, user, "create_default_template", "template", template.id, template.name)
    return template


def _get_template_for_read(db: Session, template_id: int, user: User) -> DocumentTemplate:
    template = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.project_id and not has_project_role(db, template.project_id, user):
        raise HTTPException(status_code=403, detail="Permission denied")
    return template


def _get_template_for_write(db: Session, template_id: int, user: User) -> DocumentTemplate:
    template = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.project_id and not has_project_role(db, template.project_id, user, {"manager", "editor"}):
        raise HTTPException(status_code=403, detail="Permission denied")
    return template


def _save_template_version(db: Session, template: DocumentTemplate, user: User) -> None:
    if template.version_tag:
        db.query(DocumentTemplateVersion).filter(
            DocumentTemplateVersion.template_id == template.id,
            DocumentTemplateVersion.version != template.version,
            DocumentTemplateVersion.version_tag == template.version_tag,
        ).update({"version_tag": None}, synchronize_session=False)
    exists = (
        db.query(DocumentTemplateVersion)
        .filter(DocumentTemplateVersion.template_id == template.id, DocumentTemplateVersion.version == template.version)
        .first()
    )
    if exists:
        return
    db.add(
        DocumentTemplateVersion(
            template_id=template.id,
            version=template.version,
            name=template.name,
            description=template.description,
            content=template.content,
            branch_name=template.branch_name,
            version_tag=template.version_tag,
            created_by=user.id,
        )
    )


def _delete_template_rollback_records(db: Session, template_id: int) -> None:
    bind = db.get_bind()
    inspector = inspect(bind)
    if "version_rollback_records" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("version_rollback_records")}
    reference_columns = [
        column
        for column in ("source_template_id", "target_template_id", "template_id")
        if column in columns
    ]
    if not reference_columns:
        return
    conditions = " OR ".join(f"{column} = :template_id" for column in reference_columns)
    db.execute(
        text(f"DELETE FROM version_rollback_records WHERE {conditions}"),
        {"template_id": template_id},
    )


def _normalize_branch(value: str | None) -> str:
    branch = (value or "main").strip()
    return branch[:80] or "main"


def _normalize_tag(value: str | None) -> str | None:
    tag = (value or "").strip()
    return tag[:80] or None


def _template_tag_exists(
    db: Session,
    project_id: int | None,
    name: str,
    tag: str,
    exclude_template_id: int | None = None,
) -> bool:
    query = db.query(DocumentTemplateVersion).join(DocumentTemplate).filter(
        DocumentTemplate.name == name,
        DocumentTemplate.project_id.is_(None) if project_id is None else DocumentTemplate.project_id == project_id,
        DocumentTemplateVersion.version_tag == tag,
    )
    if exclude_template_id is not None:
        query = query.filter(DocumentTemplateVersion.template_id != exclude_template_id)
    return bool(query.first())
