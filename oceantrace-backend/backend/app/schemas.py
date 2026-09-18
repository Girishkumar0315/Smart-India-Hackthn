from datetime import datetime
from typing import Optional, List, Any

from pydantic import BaseModel, EmailStr, field_validator


# ---------------------------------------------------------------- auth ----
class RegisterRequest(BaseModel):
    name: str
    organization: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain an uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain a lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain a digit")
        if all(c.isalnum() for c in v):
            raise ValueError("Password must contain a special character")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    organization: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


# ----------------------------------------------------------- investigation
class InvestigationCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    priority: str = "MEDIUM"


class InvestigationOut(BaseModel):
    id: str
    name: str
    description: str
    priority: str
    status: str
    owner_id: str
    created_at: datetime
    stages_done: List[str] = []
    satellite: Optional[dict] = None
    detection: Optional[dict] = None
    environment: Optional[dict] = None
    drift: Optional[dict] = None
    ais: Optional[dict] = None
    evidence_chain: Optional[list] = None

    class Config:
        from_attributes = True


# ------------------------------------------------------------------- AIS --
class VesselRecord(BaseModel):
    mmsi: str
    name: str
    type: str = "Unknown"
    flag: str = "Unknown"
    lat: float
    lon: float
    heading_deg: float = 0.0
    timestamp_offset_h: float = 0.0  # hours relative to detection time, negative = past


class AISAnalyzeRequest(BaseModel):
    origin_lat: float
    origin_lon: float
    spill_time_h: float          # e.g. -38 (hours relative to detection)
    drift_bearing_deg: float
    vessels: List[VesselRecord]


class VesselScore(BaseModel):
    mmsi: str
    name: str
    type: str
    flag: str
    distance_km: float
    distance_nmi: float
    spatial: int
    temporal: int
    trajectory: int
    drift_compat: int
    behavior: int
    total: int
    status: str


class AISAnalyzeResponse(BaseModel):
    funnel: List[int]
    vessels: List[VesselScore]
    compute_ms: float


# ---------------------------------------------------------------- drift --
class DriftRequest(BaseModel):
    origin_lat: float
    origin_lon: float
    area_km2: float
    wind_dir_deg: float
    wind_speed_kt: float
    current_dir_deg: float
    current_speed_kt: float


class DriftResponse(BaseModel):
    probable_origin_lat: float
    probable_origin_lon: float
    estimated_age_h: float
    origin_window: str
    spill_polygon: List[List[float]]
    forecast_polygon: List[List[float]]
    compute_ms: float


# --------------------------------------------------------------- generic --
class ErrorResponse(BaseModel):
    detail: str
