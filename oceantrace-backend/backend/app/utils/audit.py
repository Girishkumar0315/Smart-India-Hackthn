from typing import Optional
from sqlalchemy.orm import Session

from app import models


def write_audit(db: Session, user: Optional[models.User], mission_id: Optional[str], action: str):
    """Never pass password/token values into `action` — this is a hard rule,
    not just a convention, to avoid leaking secrets into the audit trail."""
    entry = models.AuditLog(
        user_email=user.email if user else None,
        role=user.role.value if user else None,
        mission_id=mission_id,
        action=action,
    )
    db.add(entry)
    db.commit()
