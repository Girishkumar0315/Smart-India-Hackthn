from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.security import require_role

router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/audit-logs")
def get_audit_logs(
    db: Session = Depends(get_db),
    limit: int = 200,
    user: models.User = Depends(require_role("ADMIN")),
):
    rows = db.query(models.AuditLog).order_by(models.AuditLog.time.desc()).limit(limit).all()
    return [
        {"time": r.time, "user_email": r.user_email, "role": r.role, "mission_id": r.mission_id, "action": r.action}
        for r in rows
    ]
