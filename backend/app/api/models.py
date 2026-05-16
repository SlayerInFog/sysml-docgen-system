import json
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.project import Project
from app.models.sysml import ModelElement, ModelRelation, SysMLModel
from app.models.user import User
from app.schemas.sysml import ModelElementOut, ModelElementUpdate, ModelGraphOut, ModelRelationOut, SysMLModelOut
from app.services.audit import write_log
from app.services.sysml_parser import parse_model_file

router = APIRouter(prefix="/models", tags=["模型管理"])
settings = get_settings()


@router.post("/upload", response_model=SysMLModelOut, status_code=201)
def upload_model(
    project_id: int = Form(...),
    name: str = Form(...),
    description: str | None = Form(None),
    file: UploadFile = File(...),
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> SysMLModel:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="权限不足")

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
        .filter(SysMLModel.project_id == project_id, SysMLModel.name == name)
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
    db.commit()
    db.refresh(model)
    write_log(db, user, "upload_model", "model", model.id, f"解析元素 {len(parsed.elements)} 个")
    return model


@router.get("", response_model=list[SysMLModelOut])
def list_models(project_id: int | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(SysMLModel).join(Project)
    if project_id:
        query = query.filter(SysMLModel.project_id == project_id)
    if user.role != "admin":
        query = query.filter(Project.owner_id == user.id)
    return query.order_by(SysMLModel.created_at.desc()).all()


@router.get("/{model_id}/elements", response_model=list[ModelElementOut])
def list_elements(model_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_model_access(db, model_id, user)
    return db.query(ModelElement).filter(ModelElement.model_id == model_id).order_by(ModelElement.type, ModelElement.name).all()


@router.get("/{model_id}/graph", response_model=ModelGraphOut)
def graph(model_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_model_access(db, model_id, user)
    elements = db.query(ModelElement).filter(ModelElement.model_id == model_id).all()
    relations = db.query(ModelRelation).filter(ModelRelation.model_id == model_id).all()
    return ModelGraphOut(
        elements=[ModelElementOut.model_validate(item) for item in elements],
        relations=[ModelRelationOut.model_validate(item) for item in relations],
    )


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
    ensure_model_access(db, element.model_id, user)
    if payload.name is not None:
        element.name = payload.name[:255]
    if payload.documentation is not None:
        element.documentation = payload.documentation
    db.commit()
    db.refresh(element)
    write_log(db, user, "update_element", "element", element.id, element.name)
    return element


def ensure_model_access(db: Session, model_id: int, user: User) -> SysMLModel:
    model = db.query(SysMLModel).join(Project).filter(SysMLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    if user.role != "admin" and model.project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="权限不足")
    return model
