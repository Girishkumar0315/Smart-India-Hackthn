import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import get_settings

settings = get_settings()

# Real "magic number" signature check — never trust the filename/extension alone.
MAGIC_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": ".png",
    b"\xff\xd8\xff": ".jpg",
    b"II*\x00": ".tif",   # little-endian TIFF/GeoTIFF
    b"MM\x00*": ".tif",   # big-endian TIFF/GeoTIFF
}


def _sniff_extension(head: bytes) -> str | None:
    for sig, ext in MAGIC_SIGNATURES.items():
        if head.startswith(sig):
            return ext
    return None


async def validate_and_save_image(file: UploadFile) -> dict:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.ALLOWED_IMAGE_EXT:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension: {ext or '(none)'}")

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_MB:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_MB} MB limit.")

    sniffed = _sniff_extension(contents[:16])
    if sniffed is None:
        raise HTTPException(status_code=400, detail="File content does not match a supported image format (invalid or corrupted file).")

    # Generate a safe, unpredictable internal filename — never trust the
    # client-provided name, and never execute/serve uploads from a static/
    # executable directory.
    safe_name = f"{uuid.uuid4().hex}{sniffed}"
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    dest_path = os.path.join(settings.UPLOAD_DIR, safe_name)
    with open(dest_path, "wb") as f:
        f.write(contents)

    return {
        "safe_name": safe_name,
        "original_name": file.filename,
        "size_kb": round(len(contents) / 1024, 1),
        "content_type": file.content_type,
        "path": dest_path,
    }
