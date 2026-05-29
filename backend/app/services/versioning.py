from sqlalchemy.orm import Session

from app.models.sysml import SysMLModel
from app.models.user import User
from app.models.versioning import VersionBranch


def sync_model_branch_head(db: Session, model: SysMLModel, user: User) -> VersionBranch:
    branch_name = (model.branch_name or "main").strip() or "main"
    branch = (
        db.query(VersionBranch)
        .filter(
            VersionBranch.project_id == model.project_id,
            VersionBranch.item_type == "model",
            VersionBranch.name == branch_name,
        )
        .order_by(VersionBranch.id.asc())
        .first()
    )
    if branch is None:
        branch = VersionBranch(
            project_id=model.project_id,
            item_type="model",
            name=branch_name,
            head_model_id=model.id,
            created_by=user.id,
        )
        db.add(branch)
    else:
        branch.head_model_id = model.id
        branch.status = "active"
    return branch


def reassign_model_branch_heads_before_delete(db: Session, model: SysMLModel) -> None:
    branches = (
        db.query(VersionBranch)
        .filter(
            VersionBranch.project_id == model.project_id,
            VersionBranch.item_type == "model",
            VersionBranch.head_model_id == model.id,
        )
        .all()
    )
    for branch in branches:
        fallback = (
            db.query(SysMLModel)
            .filter(
                SysMLModel.project_id == model.project_id,
                SysMLModel.branch_name == branch.name,
                SysMLModel.id != model.id,
            )
            .order_by(SysMLModel.version.desc(), SysMLModel.created_at.desc(), SysMLModel.id.desc())
            .first()
        )
        branch.head_model_id = fallback.id if fallback else None
