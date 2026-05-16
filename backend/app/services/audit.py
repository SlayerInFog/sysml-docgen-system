from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User


def write_log(
    db: Session,
    user: User | None,
    action: str,
    target_type: str | None = None,
    target_id: str | int | None = None,
    message: str | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            message=message,
        )
    )
    db.commit()
