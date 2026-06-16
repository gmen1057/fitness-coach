"""
Profile and health models for tracking weight, injuries, and lab results.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.models import Base


class InjuryStatus(str, enum.Enum):
    """Status of injury episodes."""
    active = "active"
    recovering = "recovering"
    resolved = "resolved"


class BodyWeightLog(Base):
    """Time-series logs of body weight and fat percentage."""

    __tablename__ = "body_weight_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    weight_kg = Column(Float, nullable=False)
    body_fat_pct = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    logged_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_body_weight_log_user_time", "user_id", "logged_at"),
    )


class InjuryEpisode(Base):
    """Logs of physical injuries and exercises to avoid."""

    __tablename__ = "injury_episodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    body_part = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(Integer, nullable=True)
    status = Column(Enum(InjuryStatus), default=InjuryStatus.active, nullable=False)

    occurred_at = Column(Date, nullable=False)
    resolved_at = Column(Date, nullable=True)

    exercises_to_avoid = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_injury_episodes_user_status", "user_id", "status"),
    )


class BloodMarker(Base):
    """Time-series lab/blood markers (lipids, hormones, CBC)."""

    __tablename__ = "blood_markers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    marker = Column(String(80), nullable=False)        # e.g., "HDL", "LDL", "estradiol"
    display_name = Column(String(160), nullable=True)  # e.g., "HDL Cholesterol"
    value_num = Column(Float, nullable=True)           # parsed numeric for trending
    value_text = Column(String(40), nullable=True)     # raw value
    unit = Column(String(40), nullable=True)
    ref_text = Column(String(80), nullable=True)       # reference range
    flag = Column(String(10), nullable=True)           # "high" | "low" | "normal"

    measured_at = Column(Date, nullable=False, index=True)
    lab_name = Column(String(160), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_blood_markers_user_marker_time", "user_id", "marker", "measured_at"),
    )
