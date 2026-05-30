from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberOut,
    ProjectMemberUpdate,
    ProjectOut,
    ProjectUpdate,
)
from app.services.audit import write_log

router = APIRouter(prefix="/projects", tags=["项目管理"])
PROJECT_MEMBER_ROLES = {"manager", "editor", "viewer"}
USER_PROJECT_ROLE_LIMITS = {
    "reader": {"viewer"},
    "author": {"manager", "editor", "viewer"},
    "admin": {"manager", "editor", "viewer"},
}


# 创建项目并设置当前用户为负责人。
@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    payload: ProjectCreate,
    user: User = Depends(require_roles("admin", "author")),
    db: Session = Depends(get_db),
) -> Project:
    exists = db.query(Project).filter(Project.code == payload.code).first()
    if exists:
        raise HTTPException(status_code=400, detail="Project code already exists")
    project = Project(name=payload.name, code=payload.code, description=payload.description, owner_id=user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    write_log(db, user, "create_project", "project", project.id, project.name)
    return project


# 按当前用户权限返回项目列表。
@router.get("", response_model=list[ProjectOut])
def list_projects(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Project]:
    query = db.query(Project)
    if user.role != "admin":
        query = query.outerjoin(ProjectMember).filter(
            or_(Project.owner_id == user.id, ProjectMember.user_id == user.id)
        )
    return query.order_by(Project.created_at.desc()).all()


# 读取单个项目详情。
@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not has_project_access(db, project, user):
        raise HTTPException(status_code=403, detail="Permission denied")
    return project


# 更新项目基础信息。
@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    project = ensure_project_manage_access(db, project_id, user)
    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    db.commit()
    db.refresh(project)
    write_log(db, user, "update_project", "project", project.id, project.name)
    return project


# 删除指定项目。
@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    project_name = project.name
    db.delete(project)
    db.commit()
    write_log(db, user, "delete_project", "project", project_id, project_name)


# 读取项目成员列表。
@router.get("/{project_id}/members", response_model=list[ProjectMemberOut])
def list_project_members(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProjectMemberOut]:
    project = get_project(project_id, user, db)
    owner = db.query(User).filter(User.id == project.owner_id).first()
    members = (
        db.query(ProjectMember)
        .join(User)
        .filter(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.created_at.desc())
        .all()
    )
    result: list[ProjectMemberOut] = []
    if owner:
        result.append(
            ProjectMemberOut(
                id=0,
                project_id=project.id,
                user_id=owner.id,
                username=owner.username,
                full_name=owner.full_name,
                email=owner.email,
                role="owner",
                created_at=project.created_at,
            )
        )
    result.extend(_member_out(member) for member in members)
    return result


# 添加项目成员并校验角色权限。
@router.post("/{project_id}/members", response_model=ProjectMemberOut, status_code=201)
def add_project_member(
    project_id: int,
    payload: ProjectMemberCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectMemberOut:
    project = ensure_project_manage_access(db, project_id, user)
    if payload.role not in PROJECT_MEMBER_ROLES:
        raise HTTPException(status_code=400, detail="Project member role must be manager, editor, or viewer")
    target_user = db.query(User).filter(User.id == payload.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    if target_user.id == project.owner_id:
        raise HTTPException(status_code=400, detail="Project owner is already a member")
    validate_project_role_for_user(target_user, payload.role)
    member = db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == target_user.id).first()
    if member:
        raise HTTPException(status_code=400, detail="User is already a project member")
    member = ProjectMember(project_id=project_id, user_id=target_user.id, role=payload.role)
    db.add(member)
    db.commit()
    db.refresh(member)
    write_log(db, user, "add_project_member", "project", project_id, f"{target_user.username}:{payload.role}")
    return _member_out(member)


# 更新项目成员角色。
@router.patch("/{project_id}/members/{member_id}", response_model=ProjectMemberOut)
def update_project_member(
    project_id: int,
    member_id: int,
    payload: ProjectMemberUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectMemberOut:
    ensure_project_manage_access(db, project_id, user)
    if payload.role not in PROJECT_MEMBER_ROLES:
        raise HTTPException(status_code=400, detail="Project member role must be manager, editor, or viewer")
    member = db.query(ProjectMember).filter(ProjectMember.id == member_id, ProjectMember.project_id == project_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Project member not found")
    validate_project_role_for_user(member.user, payload.role)
    member.role = payload.role
    db.commit()
    db.refresh(member)
    write_log(db, user, "update_project_member", "project", project_id, f"{member.user.username}:{member.role}")
    return _member_out(member)


# 移除项目成员。
@router.delete("/{project_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_member(
    project_id: int,
    member_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    ensure_project_manage_access(db, project_id, user)
    member = db.query(ProjectMember).filter(ProjectMember.id == member_id, ProjectMember.project_id == project_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Project member not found")
    member_name = member.user.username
    db.delete(member)
    db.commit()
    write_log(db, user, "remove_project_member", "project", project_id, member_name)


# 判断用户是否有项目访问权限。
def has_project_access(db: Session, project: Project, user: User) -> bool:
    if user.role == "admin" or project.owner_id == user.id:
        return True
    return (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == user.id)
        .first()
        is not None
    )


# 判断用户是否具备指定项目角色。
def has_project_role(db: Session, project_id: int, user: User, roles: set[str] | None = None) -> bool:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return False
    if user.role == "admin":
        return True
    if user.role == "reader" and roles and roles.intersection({"manager", "editor"}):
        return False
    if project.owner_id == user.id:
        return True
    query = db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id)
    if roles:
        query = query.filter(ProjectMember.role.in_(roles))
    return query.first() is not None


# 校验项目成员管理权限。
def ensure_project_manage_access(db: Session, project_id: int, user: User) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if user.role == "admin" or project.owner_id == user.id:
        return project
    member = db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id).first()
    if not member or member.role != "manager":
        raise HTTPException(status_code=403, detail="Permission denied")
    return project


# 校验系统角色允许分配的项目角色。
def validate_project_role_for_user(user: User, project_role: str) -> None:
    allowed_roles = USER_PROJECT_ROLE_LIMITS.get(user.role, {"viewer"})
    if project_role not in allowed_roles:
        raise HTTPException(status_code=400, detail="该用户全局角色不允许授予此项目角色")


# 处理 _member_out 相关逻辑。
def _member_out(member: ProjectMember) -> ProjectMemberOut:
    return ProjectMemberOut(
        id=member.id,
        project_id=member.project_id,
        user_id=member.user_id,
        username=member.user.username,
        full_name=member.user.full_name,
        email=member.user.email,
        role=member.role,
        created_at=member.created_at,
    )
