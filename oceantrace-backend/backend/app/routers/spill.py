from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.security import get_current_user, require_role, require_investigation_owner_or_admin
from app.services.detection import get_detector
from app.utils.audit import write_audit
from app.utils.uploads import validate_and_save_image

router = APIRouter(prefix="/api", tags=["spill"])


@router.post("/satellite/upload/{investigation_id}")
async def upload_satellite_image(
    investigation_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role("ADMIN", "ANALYST")),
):
    inv = db.query(models.Investigation).filter(models.Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    require_investigation_owner_or_admin(inv, user)

    saved = await validate_and_save_image(file)
    inv.satellite = {
        "file_name": saved["safe_name"],
        "original_name": saved["original_name"],
        "size_kb": saved["size_kb"],
        "content_type": saved["content_type"],
        "path": saved["path"],
    }
    stages = set(inv.stages_done or [])
    stages.add("INGEST")
    inv.stages_done = list(stages)
    db.commit()
    write_audit(db, user, inv.id, "SATELLITE IMAGE UPLOADED")
    return {"detail": "Uploaded", "satellite": inv.satellite}


@router.post("/spill/detect/{investigation_id}")
async def detect_spill(
    investigation_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role("ADMIN", "ANALYST")),
):
    inv = db.query(models.Investigation).filter(models.Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    require_investigation_owner_or_admin(inv, user)
    if not inv.satellite:
        raise HTTPException(status_code=400, detail="No satellite image has been ingested for this investigation.")

    detector = get_detector()
    with open(inv.satellite["path"], "rb") as f:
        image_bytes = f.read()
    tensor = detector.preprocess(image_bytes)
    raw = detector.predict(tensor)
    result = detector.postprocess(raw)
    inv.detection = result
    stages = set(inv.stages_done or [])
    stages.update({"DETECT", "CHARACTERIZE"})
    inv.stages_done = list(stages)
    db.commit()
    write_audit(db, user, inv.id, "SPILL DETECTION EXECUTED")
    return result


@router.post("/spill/segformer-detect")
async def segformer_detect(
    file: UploadFile = File(...),
    modality: str = "auto",
):
    """
    Direct SegFormer Vision AI Detection endpoint for SAR and Optical images.
    Supports both Sentinel-1 SAR and Normal Optical/Aerial/Drone RGB photos.
    """
    saved = await validate_and_save_image(file)
    with open(saved["path"], "rb") as f:
        image_bytes = f.read()

    detector = get_detector()
    tensor = detector.preprocess(image_bytes, modality_hint=modality)
    raw = detector.predict(tensor)
    result = detector.postprocess(raw)
    result["file_info"] = {
        "file_name": saved["original_name"],
        "size_kb": saved["size_kb"],
        "content_type": saved["content_type"],
    }
    return result

