"""Pydantic schemas for prediction, risk, incidents, reports, etc."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    rainfall_24h: float = 0.0
    rainfall_6h: float = 0.0
    rainfall_1h: float = 0.0
    rain_3d: float = 0.0
    rain_7d: float = 0.0
    soil_moisture: float = 0.0
    slope_deg: float = 0.0
    elevation_m: float = 0.0
    historical_frequency: float = 0.0  # count of past landslides
    distance_to_roads_m: float = 0.0
    vegetation_change: float = 0.0
    deformation_mm: float = 0.0
    land_cover: str = "forest"


class FactorContribution(BaseModel):
    factor: str
    contribution: float


class PredictionResponse(BaseModel):
    risk_score: float
    risk_level: str
    confidence: float
    factors: list[str]
    factor_contributions: list[FactorContribution]
    recommended_action: str
    model: str
    predicted_at: datetime


class RiskZoneOut(BaseModel):
    id: str
    name: str
    risk_score: float
    risk_level: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    district_id: Optional[str] = None
    district_name: Optional[str] = None
    village_id: Optional[str] = None
    village_name: Optional[str] = None
    population: int
    area_km2: float
    last_update: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReportCreate(BaseModel):
    report_type: str
    severity: str = "medium"
    description: Optional[str] = None
    latitude: float
    longitude: float
    device_location_manual: bool = False
    client_id: Optional[str] = None  # for offline dedupe
    incident_id: Optional[str] = None
    photos: list[str] = Field(default_factory=list)  # base64 data URLs or refs


class ReportUpdate(BaseModel):
    severity: Optional[str] = None
    description: Optional[str] = None
    sync_status: Optional[str] = None


class ReportOut(BaseModel):
    id: str
    report_type: str
    severity: str
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reported_by: Optional[str] = None
    reporter_name: Optional[str] = None
    incident_id: Optional[str] = None
    client_id: Optional[str] = None
    sync_status: str
    reported_at: datetime
    media: list[Any] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class IncidentCreate(BaseModel):
    incident_type: str
    severity: str = "medium"
    latitude: float
    longitude: float
    description: Optional[str] = None
    district_id: Optional[str] = None


class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    assigned_to: Optional[str] = None
    verification_status: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None


class IncidentOut(BaseModel):
    id: str
    incident_type: str
    status: str
    severity: str
    verification_status: str
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reported_by: Optional[str] = None
    reporter_name: Optional[str] = None
    assigned_to: Optional[str] = None
    assignee_name: Optional[str] = None
    district_id: Optional[str] = None
    reported_at: datetime
    resolved_at: Optional[datetime] = None
    priority_score: Optional[float] = None
    priority_class: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None

    model_config = {"from_attributes": True}


class RoadOut(BaseModel):
    id: str
    name: str
    road_type: str
    status: str
    population_served: int
    alternative_route: bool
    priority_score: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    district_id: Optional[str] = None
    last_status_update: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RoadStatusUpdate(BaseModel):
    status: str
    reason: Optional[str] = None


class AlertOut(BaseModel):
    id: str
    title: str
    message: str
    severity: str
    alert_type: str
    status: str
    risk_level: Optional[str] = None
    cause: Optional[str] = None
    recommended_action: Optional[str] = None
    affected_villages: Any = None
    affected_roads: Any = None
    affected_infrastructure: Any = None
    district_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SensorReadingIn(BaseModel):
    sensor_id: str
    reading_type: str
    value: float
    unit: str = ""
    api_token: Optional[str] = None
    read_at: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class SensorOut(BaseModel):
    id: str
    name: str
    sensor_type: str
    status: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    district_id: Optional[str] = None
    district_name: Optional[str] = None
    last_reading_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SensorReadingOut(BaseModel):
    id: str
    sensor_id: str
    reading_type: str
    value: float
    unit: str
    read_at: datetime
    is_anomaly: bool

    model_config = {"from_attributes": True}


class SensorCreate(BaseModel):
    name: str
    sensor_type: str
    latitude: float
    longitude: float
    district_id: Optional[str] = None


class DashboardSummary(BaseModel):
    critical_zones: int
    high_risk_zones: int
    active_incidents: int
    roads_blocked: int
    villages_at_risk: int
    active_alerts: int
    total_districts: int
    total_sensors: int
    max_risk_score: float
    updated_at: datetime


class EmergencyPriorityOut(BaseModel):
    incident_id: str
    location: str
    risk_score: float
    risk_level: str
    population_affected: int
    infrastructure_affected: list[str]
    road_accessibility: str
    num_reports: int
    priority_score: float
    priority_class: str
    recommended_response: str

    model_config = {"from_attributes": True}


class HealthOut(BaseModel):
    status: str
    api: str
    database: str
    ml_model: str
    weather_provider: str
    satellite_provider: str
    notification_provider: str
    last_sync: Optional[datetime] = None
    components: dict[str, dict[str, Any]]


class ConfigItemUpdate(BaseModel):
    key: str
    value: Any


class ChangeThresholdRequest(BaseModel):
    risk_level: str
    lower: int
    upper: int
