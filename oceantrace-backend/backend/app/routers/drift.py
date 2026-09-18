from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_role, require_investigation_owner_or_admin
from app.services.drift_engine import DriftEngine
from app.utils.audit import write_audit

router = APIRouter(prefix="/api", tags=["drift"])


@router.post("/drift/backward", response_model=schemas.DriftResponse)
def backward_drift(payload: schemas.DriftRequest, user: models.User = Depends(get_current_user)):
    """Stateless compute endpoint — the frontend supplies detection + environment
    context and gets back a probable origin. No investigation_id required, which
    keeps this reusable outside the demo's investigation-object model too."""
    engine = DriftEngine(
        wind_dir_deg=payload.wind_dir_deg, wind_speed_kt=payload.wind_speed_kt,
        current_dir_deg=payload.current_dir_deg, current_speed_kt=payload.current_speed_kt,
    )
    result = engine.estimate_origin(payload.origin_lat, payload.origin_lon, payload.area_km2)
    radius_km = max((payload.area_km2 / 3.14159) ** 0.5 * 6, 3.0)
    spill_poly = [list(engine.forward_simulation(payload.origin_lat, payload.origin_lon, 0)) for _ in range(1)]
    # Build simple polygons around origin/observed point for map rendering.
    import numpy as np
    from app.services.geo import dest_point
    def ring(center, radius, n=9):
        pts = []
        for i in range(n):
            ang = i * (360 / n)
            pts.append(list(dest_point(center[0], center[1], ang, radius)))
        return pts
    spill_polygon = ring((payload.origin_lat, payload.origin_lon), radius_km)
    forecast_center = engine.forward_simulation(payload.origin_lat, payload.origin_lon, 12)
    forecast_polygon = ring(forecast_center, radius_km * 1.8)

    return schemas.DriftResponse(
        probable_origin_lat=result["origin_lat"],
        probable_origin_lon=result["origin_lon"],
        estimated_age_h=round(result["age_h"], 1),
        origin_window=result["window"],
        spill_polygon=spill_polygon,
        forecast_polygon=forecast_polygon,
        compute_ms=round(result["compute_ms"], 3),
    )


@router.post("/origin/{investigation_id}")
def save_origin_to_investigation(
    investigation_id: str,
    payload: schemas.DriftRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role("ADMIN", "ANALYST")),
):
    inv = db.query(models.Investigation).filter(models.Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    require_investigation_owner_or_admin(inv, user)
    resp = backward_drift(payload, user)
    inv.drift = resp.model_dump()
    stages = set(inv.stages_done or [])
    stages.add("TRACE")
    inv.stages_done = list(stages)
    db.commit()
    write_audit(db, user, inv.id, "BACKWARD DRIFT ANALYSIS EXECUTED")
    return resp
