"""Risk, incident, report, road, media and alert models."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.geo import BaseGeo, utcnow


class RiskZone(BaseGeo):
    __tablename__ = "risk_zones"

    name: Mapped[str] = mapped_column(String(150))
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(20), default="VERY_LOW", index=True)
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=True)
    village_id: Mapped[str] = mapped_column(ForeignKey("villages.id"), nullable=True)
    population: Mapped[int] = mapped_column(Integer, default=0)
    area_km2: Mapped[float] = mapped_column(Float, default=0.0)
    last_update: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    district: Mapped["District"] = relationship()
    village: Mapped["Village"] = relationship()


class RiskPrediction(BaseGeo):
    __tablename__ = "risk_predictions"

    risk_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(20), default="VERY_LOW", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    factors: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    factor_contributions: Mapped[str] = mapped_column(Text, default="{}")  # JSON dict for explainability
    recommended_action: Mapped[str] = mapped_column(String(255), default="")
    model: Mapped[str] = mapped_column(String(100), default="xgboost")
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=True)


class Incident(BaseGeo):
    __tablename__ = "incidents"

    incident_type: Mapped[str] = mapped_column(String(50), index=True)  # slope_crack|movement|rockfall|...
    status: Mapped[str] = mapped_column(String(30), default="reported", index=True)  # lifecycle
    severity: Mapped[str] = mapped_column(String(20), default="medium")  # low|medium|high|critical
    description: Mapped[str] = mapped_column(Text, nullable=True)
    reported_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=True)
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=True)
    assigned_to: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|verified|rejected
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=True)  # auto_news|mobile_report|sync|manual
    source_url: Mapped[str] = mapped_column(Text, nullable=True)  # original news article link

    reporter: Mapped["User"] = relationship(foreign_keys=[reported_by], lazy="selectin")
    assignee: Mapped["User"] = relationship(foreign_keys=[assigned_to], lazy="selectin")
    reports: Mapped[list["FieldReport"]] = relationship(back_populates="incident", lazy="selectin")
    media: Mapped[list["UploadedMedia"]] = relationship(back_populates="incident", lazy="selectin")


class FieldReport(BaseGeo):
    __tablename__ = "field_reports"

    report_type: Mapped[str] = mapped_column(String(50), index=True)  # slope_crack|movement|rockfall|blocked_road|flooding|other
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    description: Mapped[str] = mapped_column(Text, nullable=True)
    reported_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=True)
    incident_id: Mapped[Optional[str]] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=True)
    client_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=True)  # offline dedupe
    sync_status: Mapped[str] = mapped_column(String(20), default="synced")  # synced|pending_sync
    device_location_manual: Mapped[bool] = mapped_column(Boolean, default=False)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    incident: Mapped[Optional["Incident"]] = relationship(back_populates="reports")
    reporter: Mapped["User"] = relationship(foreign_keys=[reported_by], lazy="selectin")
    media: Mapped[list["UploadedMedia"]] = relationship(back_populates="report", lazy="selectin")


class UploadedMedia(Base):
    __tablename__ = "uploaded_media"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(__import__("uuid").uuid4()))
    media_type: Mapped[str] = mapped_column(String(10), default="image")  # image|video
    file_key: Mapped[str] = mapped_column(String(500))
    thumbnail_key: Mapped[str] = mapped_column(String(500), nullable=True)
    original_name: Mapped[str] = mapped_column(String(255), default="")
    mime_type: Mapped[str] = mapped_column(String(100), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=True)
    incident_id: Mapped[Optional[str]] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    report_id: Mapped[Optional[str]] = mapped_column(ForeignKey("field_reports.id"), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    incident: Mapped[Optional["Incident"]] = relationship(back_populates="media")
    report: Mapped[Optional["FieldReport"]] = relationship(back_populates="media")


class Road(BaseGeo):
    __tablename__ = "roads"

    name: Mapped[str] = mapped_column(String(150))
    road_type: Mapped[str] = mapped_column(String(50), default="highway")  # highway|state|district|village
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)  # open|restricted|blocked|severely_blocked|unknown
    population_served: Mapped[int] = mapped_column(Integer, default=0)
    alternative_route: Mapped[bool] = mapped_column(Boolean, default=True)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    last_status_update: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    prediction_score: Mapped[float] = mapped_column(Float, default=0.0)
    prediction_level: Mapped[str] = mapped_column(String(20), default="low")  # low|moderate|high|critical
    last_prediction_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    district: Mapped["District"] = relationship()


class RoadStatusHistory(Base):
    __tablename__ = "road_status"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(__import__("uuid").uuid4()))
    road_id: Mapped[str] = mapped_column(ForeignKey("roads.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    changed_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Alert(BaseGeo):
    __tablename__ = "alerts"

    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), index=True)  # advisory|watch|warning|critical
    alert_type: Mapped[str] = mapped_column(String(50), default="risk")  # risk|rainfall|soil|anomaly|report|road|road_prediction|satellite
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # active|acknowledged|resolved
    risk_level: Mapped[str] = mapped_column(String(20), nullable=True)
    cause: Mapped[str] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=True)
    affected_villages: Mapped[str] = mapped_column(Text, default="[]")
    affected_roads: Mapped[str] = mapped_column(Text, default="[]")
    affected_infrastructure: Mapped[str] = mapped_column(Text, default="[]")
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    acknowledged_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=True)
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(__import__("uuid").uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=True)
    alert_id: Mapped[str] = mapped_column(ForeignKey("alerts.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(20), default="in_app")  # sms|push|email|in_app
    provider: Mapped[str] = mapped_column(String(50), default="mock")
    status: Mapped[str] = mapped_column(String(20), default="sent")  # sent|failed|queued
    recipient: Mapped[str] = mapped_column(String(255), default="")
    error: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EmergencyResponse(BaseGeo):
    __tablename__ = "emergency_response"

    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    priority_class: Mapped[str] = mapped_column(String(20), default="low")  # immediate|high|medium|low
    population_affected: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="planned")
    responder_notes: Mapped[str] = mapped_column(Text, nullable=True)

    incident: Mapped["Incident"] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(__import__("uuid").uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str] = mapped_column(String(50), default="")
    resource_id: Mapped[str] = mapped_column(String(50), default="")
    details: Mapped[str] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SystemConfig(Base):
    """Persistent key/value configuration store (risk thresholds, alert rules, etc.)."""
    __tablename__ = "system_config"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(__import__("uuid").uuid4()))
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, default="{}")  # JSON-encoded value
    description: Mapped[str] = mapped_column(String(255), default="")
    updated_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
