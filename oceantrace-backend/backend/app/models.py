import enum
import uuid
from datetime import datetime

from sqlalchemy import (Column, String, Float, Integer, Boolean, DateTime,
                         ForeignKey, Text, JSON, Enum as SAEnum)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: gen_id("USR"))
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    organization = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(SAEnum(Role), default=Role.ANALYST, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    investigations = relationship("Investigation", back_populates="owner")


class Investigation(Base):
    __tablename__ = "investigations"
    id = Column(String, primary_key=True, default=lambda: gen_id("MISSION"))
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    priority = Column(String, default="MEDIUM")
    status = Column(String, default="IN_PROGRESS")
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # JSON blobs keep the demo simple while remaining a real, queryable row.
    # In a larger production system these would be normalised into their own
    # tables (SatelliteImage, SpillDetection, DriftAnalysis, AISRecord, ...).
    satellite = Column(JSON, nullable=True)
    detection = Column(JSON, nullable=True)
    environment = Column(JSON, nullable=True)
    drift = Column(JSON, nullable=True)
    ais = Column(JSON, nullable=True)
    evidence_chain = Column(JSON, nullable=True)
    stages_done = Column(JSON, default=list)

    owner = relationship("User", back_populates="investigations")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime, default=datetime.utcnow)
    user_email = Column(String, nullable=True)
    role = Column(String, nullable=True)
    mission_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
