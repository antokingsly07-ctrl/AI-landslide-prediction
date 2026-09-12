"""Sensor + environmental data models (rainfall, soil moisture, weather, terrain, satellite)."""
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Float, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.geo import BaseGeo


def utcnow():
    return datetime.now(timezone.utc)


class Sensor(BaseGeo):
    __tablename__ = "sensors"

    name: Mapped[str] = mapped_column(String(150))
    sensor_type: Mapped[str] = mapped_column(
        String(50), default="soil_moisture"
    )  # soil_moisture|rain_gauge|tilt|ground_movement|temperature|inclinometer|piezometer|extensometer|geophone
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=True)
    api_token: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="online")  # online|offline|warning|critical
    last_reading_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    district: Mapped["District"] = relationship()
    readings: Mapped[list["SensorReading"]] = relationship(
        back_populates="sensor", lazy="selectin"
    )


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(__import__("uuid").uuid4()))
    sensor_id: Mapped[str] = mapped_column(ForeignKey("sensors.id"), index=True)
    reading_type: Mapped[str] = mapped_column(String(50))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20), default="")
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    is_anomaly: Mapped[bool] = mapped_column(default=False)

    sensor: Mapped["Sensor"] = relationship(back_populates="readings")


class RainfallRecord(BaseGeo):
    __tablename__ = "rainfall_records"

    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=True)
    amount_mm: Mapped[float] = mapped_column(Float)
    intensity: Mapped[float] = mapped_column(Float, default=0.0)  # mm/hr
    rain_1h: Mapped[float] = mapped_column(Float, default=0.0)
    rain_6h: Mapped[float] = mapped_column(Float, default=0.0)
    rain_24h: Mapped[float] = mapped_column(Float, default=0.0)
    rain_3d: Mapped[float] = mapped_column(Float, default=0.0)
    rain_7d: Mapped[float] = mapped_column(Float, default=0.0)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    source: Mapped[str] = mapped_column(String(50), default="mock")  # imd|mock|sensor
    is_demo: Mapped[bool] = mapped_column(default=True)


class SoilMoistureRecord(BaseGeo):
    __tablename__ = "soil_moisture_records"

    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=True)
    moisture_percent: Mapped[float] = mapped_column(Float)
    depth_cm: Mapped[float] = mapped_column(Float, default=30.0)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    source: Mapped[str] = mapped_column(String(50), default="mock")


class WeatherRecord(BaseGeo):
    __tablename__ = "weather_records"

    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=True)
    temperature_c: Mapped[float] = mapped_column(Float, default=0.0)
    humidity_percent: Mapped[float] = mapped_column(Float, default=0.0)
    pressure_hpa: Mapped[float] = mapped_column(Float, default=0.0)
    wind_speed: Mapped[float] = mapped_column(Float, default=0.0)
    precipitation_mm: Mapped[float] = mapped_column(Float, default=0.0)
    forecast: Mapped[str] = mapped_column(Text, nullable=True)
    warning: Mapped[str] = mapped_column(String(20), default="none")  # none|watch|warning|critical
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    source: Mapped[str] = mapped_column(String(50), default="mock")


class TerrainData(BaseGeo):
    __tablename__ = "terrain_data"

    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=True)
    slope_deg: Mapped[float] = mapped_column(Float, default=0.0)
    elevation_m: Mapped[float] = mapped_column(Float, default=0.0)
    aspect: Mapped[float] = mapped_column(Float, default=0.0)
    curvature: Mapped[float] = mapped_column(Float, default=0.0)
    land_cover: Mapped[str] = mapped_column(String(50), default="forest")
    geology: Mapped[str] = mapped_column(String(100), default="unknown")
    distance_to_roads_m: Mapped[float] = mapped_column(Float, default=0.0)


class LandslideHistory(BaseGeo):
    __tablename__ = "landslide_history"

    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=True)
    occurred_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    severity: Mapped[int] = mapped_column(Integer, default=2)  # 1 minor .. 5 catastrophic
    cause: Mapped[str] = mapped_column(String(50), default="rainfall")
    description: Mapped[str] = mapped_column(Text, nullable=True)
    year: Mapped[int] = mapped_column(Integer, default=2020)


class SatelliteObservation(BaseGeo):
    __tablename__ = "satellite_observations"

    source: Mapped[str] = mapped_column(String(50), default="sentinel")  # sentinel|landsat|...
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    vegetation_change: Mapped[float] = mapped_column(Float, default=0.0)  # normalized diff
    land_cover: Mapped[str] = mapped_column(String(50), default="unknown")
    deformation_mm: Mapped[float] = mapped_column(Float, default=0.0)
    moisture_index: Mapped[float] = mapped_column(Float, default=0.0)
    is_demo: Mapped[bool] = mapped_column(default=True)
