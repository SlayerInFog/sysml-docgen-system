from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.audit import write_log

router = APIRouter(prefix="/projects", tags=["项目管理"])


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    payload: ProjectCreate,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> Project:
    exists = db.query(Project).filter(Project.code == payload.code).first()
    if exists:
        raise HTTPException(status_code=400, detail="项目编码已存在")
    project = Project(name=payload.name, code=payload.code, description=payload.description, owner_id=user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    write_log(db, user, "create_project", "project", project.id, project.name)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Project]:
    query = db.query(Project)
    if user.role != "admin":
        query = query.filter(Project.owner_id == user.id)
    return query.order_by(Project.created_at.desc()).all()


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="权限不足")
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    project = get_project(project_id, user, db)
    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    db.commit()
    db.refresh(project)
    write_log(db, user, "update_project", "project", project.id, project.name)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    project = get_project(project_id, user, db)
    project_name = project.name
    db.delete(project)
    db.commit()
    write_log(db, user, "delete_project", "project", project_id, project_name)
