from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.security import get_current_user, require_role, require_investigation_owner_or_admin
from app.utils.audit import write_audit

router = APIRouter(prefix="/api/reports", tags=["reports"])

LEGAL_DISCLAIMER = (
    "This system provides analytical and investigative support based on satellite "
    "observations, environmental data, and AIS correlations. Correlation does not "
    "establish legal responsibility or causation. Results should be independently "
    "verified by qualified investigators."
)


@router.post("/generate/{investigation_id}")
def generate_report(
    investigation_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role("ADMIN", "ANALYST")),
):
    inv = db.query(models.Investigation).filter(models.Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    require_investigation_owner_or_admin(inv, user)
    if not inv.ais:
        raise HTTPException(status_code=400, detail="Cannot generate report before AIS ranking has run.")

    top = inv.ais["vessels"][0] if inv.ais.get("vessels") else None
    report = {
        "mission_id": inv.id,
        "executive_summary": (
            f"A probable oil slick was identified with {inv.detection['confidence']}% model "
            f"confidence, covering an estimated {inv.detection['area_km2']} km². "
            + (f"Top candidate: {top['name']} at {top['total']}/100 composite correlation." if top else "")
        ),
        "mission": {"name": inv.name, "description": inv.description, "priority": inv.priority, "owner_id": inv.owner_id},
        "detection": inv.detection,
        "environment": inv.environment,
        "drift": inv.drift,
        "ais": inv.ais,
        "evidence_chain": inv.evidence_chain,
        "disclaimer": LEGAL_DISCLAIMER,
    }
    inv.status = "COMPLETE"
    stages = set(inv.stages_done or [])
    stages.add("REPORT")
    inv.stages_done = list(stages)
    db.commit()
    write_audit(db, user, inv.id, "INVESTIGATION REPORT GENERATED")
    return report
