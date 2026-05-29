from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogOut

router = APIRouter(prefix="/audit", tags=["日志管理"])


@router.get("/logs", response_model=list[AuditLogOut])
def logs(
    action: str | None = None,
    target_type: str | None = None,
    user_id: int | None = None,
    keyword: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(10, ge=1, le=1000),
    _: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if target_type:
        query = query.filter(AuditLog.target_type == target_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if start_time:
        query = query.filter(AuditLog.created_at >= start_time)
    if end_time:
        query = query.filter(AuditLog.created_at <= end_time)
    if keyword:
        pattern = f"%{keyword}%"
        query = query.filter(
            or_(
                AuditLog.action.like(pattern),
                AuditLog.target_type.like(pattern),
                AuditLog.target_id.like(pattern),
                AuditLog.message.like(pattern),
            )
        )
    return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
