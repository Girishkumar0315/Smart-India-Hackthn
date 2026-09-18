from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_role, require_investigation_owner_or_admin
from app.utils.audit import write_audit

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


@router.post("", response_model=schemas.InvestigationOut, status_code=201)
def create_investigation(
    payload: schemas.InvestigationCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role("ADMIN", "ANALYST")),
):
    inv = models.Investigation(
        name=payload.name, description=payload.description or "",
        priority=payload.priority, owner_id=user.id, stages_done=["INGEST"],
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    write_audit(db, user, inv.id, "INVESTIGATION CREATED")
    return inv


@router.get("", response_model=List[schemas.InvestigationOut])
def list_investigations(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    q = db.query(models.Investigation)
    if user.role.value != "ADMIN":
        q = q.filter(models.Investigation.owner_id == user.id)
    return q.order_by(models.Investigation.created_at.desc()).all()


@router.get("/{investigation_id}", response_model=schemas.InvestigationOut)
def get_investigation(investigation_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    inv = db.query(models.Investigation).filter(models.Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    require_investigation_owner_or_admin(inv, user)
    return inv
