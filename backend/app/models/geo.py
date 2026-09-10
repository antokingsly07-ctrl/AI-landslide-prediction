"""Core, geo, user and role models."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text, DateTime, Integer, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow():
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class BaseGeo(TimestampMixin, Base):
    """Abstract base for any entity that has a geographic location."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    # PostGIS geometry WKT string (production). Store EPSG:4326.
    geometry: Mapped[str] = mapped_column(Text, nullable=True, comment="PostGIS geometry WKT")


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    users: Mapped[list["User"]] = relationship(
        back_populates="role", lazy="selectin"
    )


class State(Base, TimestampMixin):
    __tablename__ = "states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

    districts: Mapped[list["District"]] = relationship(back_populates="state", lazy="selectin")


class District(Base, TimestampMixin):
    __tablename__ = "districts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=True)
    state_id: Mapped[str] = mapped_column(ForeignKey("states.id"))
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    population: Mapped[int] = mapped_column(Integer, default=0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)

    state: Mapped["State"] = relationship(back_populates="districts")
    villages: Mapped[list["Village"]] = relationship(back_populates="district", lazy="selectin")
    roads: Mapped[list["Road"]] = relationship(back_populates="district", lazy="selectin")
    sensors: Mapped[list["Sensor"]] = relationship(back_populates="district", lazy="selectin")


class Village(Base, TimestampMixin):
    __tablename__ = "villages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(150), index=True)
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    population: Mapped[int] = mapped_column(Integer, default=0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)

    district: Mapped["District"] = relationship(back_populates="villages")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(30), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"))
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    fcm_token: Mapped[str] = mapped_column(Text, nullable=True)

    role: Mapped["Role"] = relationship(back_populates="users", lazy="selectin")
    district: Mapped["District"] = relationship(lazy="selectin")


class GeographicZone(Base, TimestampMixin):
    """Area mask / catchment / administrative polygon overlays."""

    __tablename__ = "geographic_zones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(150))
    zone_type: Mapped[str] = mapped_column(String(50), default="catchment")  # catchment|block|range
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=True)
    geometry: Mapped[str] = mapped_column(Text, nullable=True)  # WKT polygon


class Infrastructure(Base, TimestampMixin):
    """Hospitals, schools, emergency services, bridges etc."""

    __tablename__ = "infrastructure"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(150))
    infra_type: Mapped[str] = mapped_column(String(50), index=True)  # hospital|school|bridge|...
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=True)
    village_id: Mapped[str] = mapped_column(ForeignKey("villages.id"), nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    importance: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    population_served: Mapped[int] = mapped_column(Integer, default=0)
    geometry: Mapped[str] = mapped_column(Text, nullable=True)
