from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_role, require_investigation_owner_or_admin
from app.services.ais_analyzer import AISAnalyzer
from app.utils.audit import write_audit

router = APIRouter(prefix="/api/ais", tags=["ais"])


@router.post("/analyze", response_model=schemas.AISAnalyzeResponse)
def analyze_ais(payload: schemas.AISAnalyzeRequest, user: models.User = Depends(get_current_user)):
    """Stateless, single-batch, numpy-vectorised scoring — this is the
    'efficient backend' counterpart to the client-side JS loop: N vessels
    are scored in one array pass instead of N Python-loop iterations,
    so this scales to a real AIS corpus without linear wall-clock blowup
    per request beyond numpy's own vectorised cost."""
    analyzer = AISAnalyzer(
        origin_lat=payload.origin_lat, origin_lon=payload.origin_lon,
        spill_time_h=payload.spill_time_h, drift_bearing_deg=payload.drift_bearing_deg,
    )
    scored, funnel = analyzer.rank_candidates(payload.vessels)
    return schemas.AISAnalyzeResponse(funnel=funnel, vessels=scored, compute_ms=round(analyzer.last_compute_ms, 3))


@router.post("/analyze/{investigation_id}", response_model=schemas.AISAnalyzeResponse)
def analyze_ais_for_investigation(
    investigation_id: str,
    payload: schemas.AISAnalyzeRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role("ADMIN", "ANALYST")),
):
    inv = db.query(models.Investigation).filter(models.Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    require_investigation_owner_or_admin(inv, user)
    resp = analyze_ais(payload, user)
    inv.ais = resp.model_dump()
    stages = set(inv.stages_done or [])
    stages.update({"CORRELATE", "RANK"})
    inv.stages_done = list(stages)
    db.commit()
    write_audit(db, user, inv.id, "AIS ANALYSIS EXECUTED")
    return resp


@router.get("/vessels/candidates/{investigation_id}")
def get_candidates(investigation_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    inv = db.query(models.Investigation).filter(models.Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    require_investigation_owner_or_admin(inv, user)
    if not inv.ais:
        raise HTTPException(status_code=404, detail="No verified result is available for this investigation.")
    return inv.ais["vessels"]
