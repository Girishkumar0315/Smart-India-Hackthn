from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import (hash_password, verify_password, create_access_token,
                           create_refresh_token, decode_token, get_current_user)
from app.config import get_settings
from app.utils.ratelimit import rate_limit
from app.utils.audit import write_audit

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = models.User(
        email=payload.email,
        name=payload.name,
        organization=payload.organization,
        password_hash=hash_password(payload.password),
        role=models.Role.ANALYST,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    write_audit(db, user, None, "ACCOUNT REGISTERED")
    return user


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit(f"login:{request.client.host if request.client else 'unknown'}", settings.AUTH_RATE_LIMIT)
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        write_audit(db, None, None, f"FAILED LOGIN ATTEMPT ({payload.email})")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    user.last_login_at = datetime.utcnow()
    db.commit()
    write_audit(db, user, None, "LOGIN")
    return schemas.TokenResponse(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")
    user = db.query(models.User).filter(models.User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return schemas.TokenResponse(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
def logout(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    write_audit(db, user, None, "LOGOUT")
    # Stateless JWT: real revocation needs a server-side denylist/short TTL,
    # documented in README as a known limitation of this demo.
    return {"detail": "Signed out. Discard the token client-side."}


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user
