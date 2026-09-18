from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db, SessionLocal
from app import models
from app.security import hash_password
from app.routers import auth, investigations, spill, drift, ais, reports, audit

settings = get_settings()

app = FastAPI(
    title="OceanTrace AI API",
    description="Maritime forensic intelligence backend — SIH26143 reference implementation.",
    version="0.9.0-prototype",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, investigations.router, spill.router, drift.router, ais.router, reports.router, audit.router):
    app.include_router(r)


@app.on_event("startup")
def on_startup():
    init_db()
    _seed_demo_users()


def _seed_demo_users():
    """Seed the same three demo accounts used by the frontend prototype,
    but with real bcrypt hashing this time — passwords are never stored
    in plaintext, even in the demo."""
    db = SessionLocal()
    try:
        demo_accounts = [
            ("admin@oceantrace.ai", "Admin@123", "Admin Officer", "NTRO", models.Role.ADMIN),
            ("analyst@oceantrace.ai", "Analyst@123", "R. Sharma", "NTRO Maritime Cell", models.Role.ANALYST),
            ("viewer@oceantrace.ai", "Viewer@123", "Field Viewer", "Coast Guard Liaison", models.Role.VIEWER),
        ]
        for email, pw, name, org, role in demo_accounts:
            if not db.query(models.User).filter(models.User.email == email).first():
                db.add(models.User(email=email, name=name, organization=org, role=role, password_hash=hash_password(pw)))
        db.commit()
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "operational", "service": "OceanTrace AI API", "env": settings.ENV}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    # Never leak internal stack traces to the client.
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})
