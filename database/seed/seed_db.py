"""Seed production-grade real data for North-Eastern India.

Only real data sources are used; nothing is simulated:

  * States / districts / villages  - real named administrative units of NE India
  * Terrain  - SRTM elevation via Open-Meteo (keyless)
  * Rainfall / soil moisture / weather - NASA POWER (MERRA-2 satellite-assimilated
    reanalysis, keyless)
  * Landslide history  - NASA Global Landslide Catalog (real events)
  * Risk zones  - computed by the platform's risk engine from the real data above

Sources that fail are skipped rather than faked. A one-time migration marker in
SystemConfig purges the legacy demo dataset, then the real seed runs once.
"""
import csv
import io
import json
import urllib.request
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.environment import (
    LandslideHistory,
    RainfallRecord,
    Sensor,
    SensorReading,
    SoilMoistureRecord,
    TerrainData,
    WeatherRecord,
)
from app.models.geo import District, Infrastructure, Role, State, User, Village
from app.models.risk import (
    Alert,
    AuditLog,
    EmergencyResponse,
    FieldReport,
    Incident,
    UploadedMedia,
    NotificationLog,
    RiskPrediction,
    RiskZone,
    Road,
    RoadStatusHistory,
    SystemConfig,
)
from app.services.nasa_power_service import get_daily_series, get_recent
from app.services.terrain_service import get_terrain


def utcnow():
    return datetime.now(timezone.utc)


# Real NE India states with genuine districts (centroids approximate)
STATES = [
    {"code": "AS", "name": "Assam", "districts": [
        {"name": "Kamrup Metropolitan", "lat": 26.14, "lon": 91.73, "pop": 1253938},
        {"name": "Dima Hasao", "lat": 25.55, "lon": 93.10, "pop": 213529},
        {"name": "Cachar", "lat": 24.81, "lon": 92.80, "pop": 1733617},
        {"name": "Karimganj", "lat": 24.87, "lon": 92.36, "pop": 1228686},
    ]},
    {"code": "ML", "name": "Meghalaya", "districts": [
        {"name": "East Khasi Hills", "lat": 25.57, "lon": 91.88, "pop": 825922},
        {"name": "West Garo Hills", "lat": 25.52, "lon": 90.22, "pop": 643291},
        {"name": "Ri Bhoi", "lat": 25.85, "lon": 91.87, "pop": 258840},
    ]},
    {"code": "MZ", "name": "Mizoram", "districts": [
        {"name": "Aizawl", "lat": 23.73, "lon": 92.72, "pop": 404821},
        {"name": "Lunglei", "lat": 22.88, "lon": 92.74, "pop": 161428},
    ]},
    {"code": "TR", "name": "Tripura", "districts": [
        {"name": "Dhalai", "lat": 23.83, "lon": 91.93, "pop": 378230},
        {"name": "Gomati", "lat": 23.53, "lon": 91.48, "pop": 436866},
    ]},
    {"code": "NL", "name": "Nagaland", "districts": [
        {"name": "Kohima", "lat": 25.67, "lon": 94.11, "pop": 267988},
        {"name": "Dimapur", "lat": 25.91, "lon": 93.73, "pop": 379769},
    ]},
    {"code": "MN", "name": "Manipur", "districts": [
        {"name": "Churachandpur", "lat": 24.33, "lon": 93.69, "pop": 271843},
        {"name": "Imphal West", "lat": 24.80, "lon": 93.94, "pop": 517992},
    ]},
]

ROLES = [
    ("super_admin", "Platform administrator with full access"),
    ("district_admin", "District-level administration"),
    ("disaster_mgmt", "Disaster management authority"),
    ("field_official", "Field officials and reporters"),
    ("citizen", "Public users"),
]

# Real settlements (village / town) in the seeded districts
REAL_VILLAGES = [
    ("Cherrapunjee", "ML", "East Khasi Hills", 25.2805, 91.7281),
    ("Mawphlang", "ML", "East Khasi Hills", 25.2156, 91.7531),
    ("Mawsynram", "ML", "East Khasi Hills", 25.3008, 91.5833),
    ("Laitlyngkot", "ML", "East Khasi Hills", 25.1950, 91.7920),
    ("Pynursla", "ML", "East Khasi Hills", 25.3000, 91.8900),
    ("Dawki", "ML", "East Khasi Hills", 25.1833, 92.0190),
    ("Tura", "ML", "West Garo Hills", 25.5000, 90.2028),
    ("Nongpoh", "ML", "Ri Bhoi", 25.9000, 91.8800),
    ("Haflong", "AS", "Dima Hasao", 25.1647, 92.9310),
    ("Silchar", "AS", "Cachar", 24.8271, 92.7970),
    ("Karimganj", "AS", "Karimganj", 24.8700, 92.3567),
    ("Aizawl", "MZ", "Aizawl", 23.7271, 92.7176),
    ("Lunglei", "MZ", "Lunglei", 22.8810, 92.7420),
    ("Kamalpur", "TR", "Dhalai", 24.1900, 91.8000),
    ("Udaipur", "TR", "Gomati", 23.5400, 91.4800),
    ("Kohima", "NL", "Kohima", 25.6747, 94.1086),
    ("Dimapur", "NL", "Dimapur", 25.9097, 93.7314),
    ("Churachandpur", "MN", "Churachandpur", 24.3333, 93.6900),
    ("Imphal", "MN", "Imphal West", 24.8170, 93.9368),
]

NE_STATES = {"Assam", "Meghalaya", "Mizoram", "Tripura", "Nagaland", "Manipur",
             "Arunachal Pradesh", "Sikkim"}
NE_BBOX = {"lat_min": 21.0, "lat_max": 29.5, "lon_min": 88.5, "lon_max": 97.6}
GLC_CSV_URL = "https://data.nasa.gov/docs/legacy/Global_Landslide_Catalog_Export/Global_Landslide_Catalog_Export_rows.csv"
MIGRATION_KEY = "real_data_generation"


def ensure_roles(db: Session) -> dict[str, Role]:
    roles = {}
    for name, desc in ROLES:
        obj = db.scalar(select(Role).where(Role.name == name))
        if not obj:
            obj = Role(name=name, description=desc)
            db.add(obj)
        roles[name] = obj
    db.commit()
    return roles


def ensure_geo(db: Session) -> tuple[dict[str, State], dict[tuple, District], list[Village]]:
    """Real states, districts and villages (idempotent upsert)."""
    state_objs = {}
    district_objs = {}
    villages = []
    for st in STATES:
        so = db.scalar(select(State).where(State.code == st["code"]))
        if not so:
            so = State(code=st["code"], name=st["name"])
            db.add(so)
            db.flush()
        state_objs[st["code"]] = so
        for d in st["districts"]:
            code = f"{st['code']}-{d['name']}"
            di = db.scalar(select(District).where(District.code == code))
            if not di:
                di = District(code=code, name=d["name"], state_id=so.id)
                db.add(di)
            di.latitude = d["lat"]
            di.longitude = d["lon"]
            di.population = d["pop"]
            di.risk_score = 0.0
            db.flush()
            district_objs[(st["code"], d["name"])] = di
    db.commit()

    # Real villages: insert only the ones that are missing
    for vname, scode, dname, lat, lon in REAL_VILLAGES:
        di = district_objs.get((scode, dname))
        if di is None:
            continue
        existing = db.scalar(select(Village).where(
            Village.name == vname, Village.district_id == di.id))
        if existing:
            villages.append(existing)
            continue
        v = Village(
            name=vname, district_id=di.id, latitude=lat, longitude=lon,
            population=0, risk_score=0.0,
        )
        db.add(v)
        villages.append(v)
    db.commit()
    return state_objs, district_objs, villages


def seed_terrain(db: Session, district_objs: dict, villages: list[Village]) -> int:
    """Real SRTM elevation/slope for every district and village."""
    if db.scalar(select(TerrainData).limit(1)):
        return 0
    points = []
    for di in district_objs.values():
        points.append((di.name, di.latitude, di.longitude, di))
    for v in villages:
        points.append((v.name, v.latitude, v.longitude, v))
    count = 0
    for name, lat, lon, ref in points:
        try:
            t = get_terrain(lat, lon)
            db.add(TerrainData(
                latitude=lat, longitude=lon,
                district_id=ref.id if isinstance(ref, District) else ref.district_id,
                slope_deg=t["slope_deg"], elevation_m=t["elevation_m"],
                aspect=t["aspect"], curvature=0.0, land_cover="unknown",
                geology="unknown", distance_to_roads_m=0.0,
            ))
            count += 1
        except Exception as exc:  # pragma: no cover - network failure
            print(f"Terrain fetch skipped for {name}: {exc}")
    db.commit()
    print(f"Seeded {count} real SRTM terrain rows.")
    return count


def seed_power_environment(db: Session, district_objs: dict) -> int:
    """Real NASA POWER daily rainfall/soil-moisture/weather for the last 8 days."""
    if db.scalar(select(RainfallRecord).limit(1)):
        return 0
    count = 0
    for st, di in district_objs.items():
        try:
            rows = get_daily_series(di.latitude, di.longitude, days=8)
        except Exception as exc:  # pragma: no cover - network failure
            print(f"NASA POWER fetch skipped for {di.name}: {exc}")
            continue
        rain3 = []
        rain7 = []
        for row in rows:
            if row["rain_mm"] is not None:
                rain3.append(row["rain_mm"])
                rain7.append(row["rain_mm"])
            rain3 = rain3[-3:]
            rain7 = rain7[-7:]
            date = datetime.strptime(row["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            db.add(RainfallRecord(
                latitude=di.latitude, longitude=di.longitude, district_id=di.id,
                amount_mm=row["rain_mm"] or 0.0, intensity=0.0,
                rain_1h=0.0, rain_6h=0.0,
                rain_24h=row["rain_mm"] or 0.0,
                rain_3d=round(sum(rain3), 1) if rain3 else 0.0,
                rain_7d=round(sum(rain7), 1) if rain7 else 0.0,
                observed_at=date, source="nasa-power", is_demo=False,
            ))
            if row["soil_moisture_pct"] is not None:
                db.add(SoilMoistureRecord(
                    latitude=di.latitude, longitude=di.longitude, district_id=di.id,
                    moisture_percent=row["soil_moisture_pct"], depth_cm=30.0,
                    observed_at=date, source="nasa-power",
                ))
            if row["temperature_c"] is not None:
                db.add(WeatherRecord(
                    latitude=di.latitude, longitude=di.longitude, district_id=di.id,
                    temperature_c=row["temperature_c"],
                    humidity_percent=row["humidity_pct"] or 0.0,
                    pressure_hpa=0.0, wind_speed=0.0,
                    precipitation_mm=row["rain_mm"] or 0.0,
                    forecast="", warning="none",
                    observed_at=date, source="nasa-power",
                ))
            count += 1
    db.commit()
    print(f"Seeded {count} real NASA POWER environmental records.")
    return count


def _nearest_district(district_objs: dict, lat: float, lon: float, max_deg: float = 1.5):
    best = None
    best_d = max_deg
    for di in district_objs.values():
        d = ((di.latitude - lat) ** 2 + (di.longitude - lon) ** 2) ** 0.5
        if d < best_d:
            best_d = d
            best = di
    return best


def _parse_glc_date(value: str) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _glc_severity(size: str, deaths) -> int:
    s = (size or "").lower()
    if "very_large" in s:
        return 5
    if "large" in s:
        return 4
    if "medium" in s:
        return 3
    if "small" in s:
        return 2
    try:
        if int(deaths or 0) >= 10:
            return 4
    except (TypeError, ValueError):
        pass
    return 2


def _glc_cause(trigger: str) -> str:
    t = (trigger or "").lower()
    if "earthquake" in t:
        return "earthquake"
    if "human" in t or "anthropogenic" in t or "construction" in t:
        return "human_activity"
    if "rain" in t or "downpour" in t or "monsoon" in t or "storm" in t or "cyclone" in t:
        return "rainfall"
    if "mine" in t:
        return "human_activity"
    return "rainfall"


def seed_landslides(db: Session, district_objs: dict) -> int:
    """Real landslide history from the NASA Global Landslide Catalog (NE India)."""
    if db.scalar(select(LandslideHistory).limit(1)):
        return 0
    try:
        with urllib.request.urlopen(GLC_CSV_URL, timeout=90) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:  # pragma: no cover - network / firewall failure
        print(f"NASA GLC fetch skipped: {exc}")
        return 0

    events = []
    seen = set()
    for row in csv.DictReader(io.StringIO(raw)):
        try:
            lat = float(row.get("latitude") or "")
            lon = float(row.get("longitude") or "")
        except (TypeError, ValueError):
            continue
        if not (NE_BBOX["lat_min"] <= lat <= NE_BBOX["lat_max"]
                and NE_BBOX["lon_min"] <= lon <= NE_BBOX["lon_max"]):
            continue
        state = (row.get("admin_division_name") or "").strip()
        country = (row.get("country_name") or "").strip()
        if country.lower() != "india" and state not in NE_STATES:
            continue
        occurred = _parse_glc_date(row.get("event_date"))
        if occurred is None:
            continue
        eid = row.get("event_id") or ""
        if eid and eid in seen:
            continue
        seen.add(eid)
        events.append((occurred, lat, lon, row))

    events.sort(key=lambda e: e[0], reverse=True)
    count = 0
    for occurred, lat, lon, row in events[:120]:
        di = _nearest_district(district_objs, lat, lon)
        title = (row.get("event_title") or "").strip()
        loc = (row.get("location_description") or "").strip()
        deaths = (row.get("fatality_count") or "").strip()
        desc = f"{title} — {loc}".strip(" —")
        db.add(LandslideHistory(
            latitude=lat, longitude=lon,
            district_id=di.id if di else None,
            occurred_on=occurred,
            severity=_glc_severity(row.get("landslide_size"), deaths),
            cause=_glc_cause(row.get("landslide_trigger")),
            description=(desc or None),
            year=occurred.year,
        ))
        count += 1
    db.commit()
    print(f"Seeded {count} real NASA GLC landslide events.")
    return count


def seed_risk_zones(db: Session, district_objs: dict, villages: list[Village]) -> int:
    """Risk zones computed from real terrain / rainfall / soil moisture."""
    if db.scalar(select(RiskZone).limit(1)):
        return 0
    from app.ml.risk_utils import risk_level_for_score

    count = 0
    for v in villages:
        slope = None
        td = db.scalar(select(TerrainData).where(
            TerrainData.latitude == v.latitude, TerrainData.longitude == v.longitude))
        if td:
            slope = td.slope_deg
        try:
            recent = get_recent(v.latitude, v.longitude, days=7)
        except Exception as exc:  # pragma: no cover - network failure
            print(f"Risk-data fetch skipped for {v.name}: {exc}")
            recent = None
        if slope is None or recent is None or recent.get("soil_moisture_pct") is None:
            continue
        slope_contrib = min(40.0, slope / 45.0 * 40.0)
        rain_contrib = min(35.0, (recent.get("rain_7d") or 0.0) / 300.0 * 35.0)
        soil_contrib = min(25.0, recent.get("soil_moisture_pct", 0.0) / 95.0 * 25.0)
        score = round(min(100.0, slope_contrib + rain_contrib + soil_contrib), 1)
        level = risk_level_for_score(score)
        db.add(RiskZone(
            name=f"{v.name} Slope Stability Zone",
            risk_score=score, risk_level=level,
            latitude=v.latitude, longitude=v.longitude,
            district_id=v.district_id, village_id=v.id,
            population=v.population, area_km2=0.0,
        ))
        v.risk_score = score
        db.flush()
        count += 1
    db.commit()
    print(f"Computed {count} real-data risk zones.")
    return count


def _safe_delete(db: Session, statement, label: str) -> None:
    """Execute a DELETE best-effort so a single bad table never aborts the
    whole migration (missing/mismatched schema can otherwise block the purge)."""
    try:
        db.execute(statement)
    except Exception as exc:  # pragma: no cover - depends on deployed schema
        db.rollback()
        print(f"Purge skipped [{label}]: {exc}")


def remove_demo_data(db: Session) -> None:
    """Purge the legacy demo dataset so only real data remains."""
    for stmt, label in (
        (delete(NotificationLog), "notification_logs"),
        (delete(EmergencyResponse), "emergency_responses"),
        (delete(FieldReport), "field_reports"),
        (delete(Alert), "alerts"),
        (delete(Incident), "incidents"),
        (delete(RiskPrediction), "risk_predictions"),
        (delete(RiskZone), "risk_zones"),
        (delete(Infrastructure), "infrastructure"),
        (delete(Road), "roads"),
        (delete(RoadStatusHistory), "road_status_history"),
        (delete(SensorReading), "sensor_readings"),
        (delete(Sensor), "sensors"),
        (delete(LandslideHistory), "landslide_history"),
        (delete(TerrainData), "terrain_data"),
        (delete(Village).where(Village.name.notin_([r[0] for r in REAL_VILLAGES])), "villages"),
        (delete(RainfallRecord).where(RainfallRecord.is_demo == True), "rainfall"),  # noqa: E712
        (delete(SoilMoistureRecord).where(SoilMoistureRecord.source == "mock"), "soil_moisture"),
        (delete(WeatherRecord).where(WeatherRecord.source == "mock"), "weather"),
        # Tables that hold user references (audit, media, system config). These
        # must go before the users purge or DELETE FROM users violates the FK.
        (delete(AuditLog), "audit_logs"),
        (delete(UploadedMedia), "uploaded_media"),
        (delete(SystemConfig), "system_configs"),
    ):
        _safe_delete(db, stmt, label)
    # Migration purge removes every pre-migration account: any account created
    # before real-data migration belongs to the legacy demo era. A real super
    # admin is created afterwards via BOOTSTRAP_ADMIN_* or first registration.
    user_count = db.scalar(select(func.count(User.id))) or 0
    try:
        db.execute(delete(User))
    except Exception as exc:  # pragma: no cover - report the real constraint
        db.rollback()
        raise RuntimeError(f"user purge failed: {exc!r}") from exc
    db.commit()
    print(f"Purged demo data (removed {user_count} pre-migration accounts).")


def has_demo_leftovers(db: Session) -> bool:
    return (db.scalar(select(func.count(User.id)).where(User.email.like("%@landslide.demo"))) or 0) > 0


def seed(db: Session):
    ensure_roles(db)
    state_objs, district_objs, villages = ensure_geo(db)
    seed_terrain(db, district_objs, villages)
    seed_power_environment(db, district_objs)
    seed_landslides(db, district_objs)
    seed_risk_zones(db, district_objs, villages)


def ensure_bootstrap_admin() -> None:
    """Create a real super admin from environment variables (if configured)."""
    from app.db.session import SessionLocal as _SL

    db = _SL()
    try:
        email = (settings.BOOTSTRAP_ADMIN_EMAIL or "").strip().lower()
        password = settings.BOOTSTRAP_ADMIN_PASSWORD or ""
        if not email or not password:
            return
        if db.scalar(select(User).where(User.email == email)):
            return
        role = db.scalar(select(Role).where(Role.name == "super_admin"))
        if role is None:
            role = Role(name="super_admin", description="Platform administrator with full access")
            db.add(role)
            db.commit()
        db.add(User(
            email=email,
            full_name=settings.BOOTSTRAP_ADMIN_NAME or "Administrator",
            hashed_password=hash_password(password),
            role_id=role.id,
            preferred_language="en",
        ))
        db.commit()
        print(f"Created bootstrapped super admin ({email}).")
    except Exception as exc:  # pragma: no cover
        print(f"Bootstrap admin skipped: {exc}")
    finally:
        db.close()


def run_migration():
    """Synchronous, fast one-time migration: purge demo data + reference geo,
    then mark the real-data generation. Called at startup so demo accounts are
    gone before the API serves requests. The marker is only written after the
    purge is *verified*, so a partially-failed purge retries on the next boot."""
    db = SessionLocal()
    try:
        marker = db.scalar(select(SystemConfig).where(SystemConfig.key == MIGRATION_KEY))
        marker_err = None
        if marker is not None:
            marker_err = (json.loads(marker.value) or {}).get("error")
        needs_purge = (
            marker is None
            or (marker_err is not None)
            or has_demo_leftovers(db)
        )
        if needs_purge:
            print("Real-data migration: purging legacy demo dataset…")
            remove_demo_data(db)
            if has_demo_leftovers(db):
                raise RuntimeError("purge left demo-era accounts behind")
            ensure_roles(db)
            ensure_geo(db)
            verbose = {
                "generation": 1,
                "at": utcnow().isoformat(),
                "error": None,
                "purged_users": True,
            }
        else:
            ensure_roles(db)
            ensure_geo(db)
            verbose = {"generation": 1, "at": (marker.value and None) or None,
                       "error": None}
        current = db.scalar(select(SystemConfig).where(SystemConfig.key == MIGRATION_KEY))
        if current is None:
            db.add(SystemConfig(
                key=MIGRATION_KEY,
                value=json.dumps(verbose),
                description="Real-data seed generation marker",
            ))
        else:
            current.value = json.dumps(verbose)
        db.commit()
        print("Real-data migration complete.")
    except Exception as exc:  # pragma: no cover - report diagnostic through health
        import traceback

        traceback.print_exc()
        try:
            current = db.scalar(select(SystemConfig).where(SystemConfig.key == MIGRATION_KEY))
            failing = {
                "generation": 1,
                "at": utcnow().isoformat(),
                "error": repr(exc),
            }
            if current is None:
                db.add(SystemConfig(
                    key=MIGRATION_KEY,
                    value=json.dumps(failing),
                    description="Real-data seed generation marker (migration error)",
                ))
            else:
                current.value = json.dumps(failing)
            db.commit()
        except Exception:  # pragma: no cover
            pass
        raise
    finally:
        db.close()


def run_real_data_fill():
    """Heavy real-data population (SRTM, NASA POWER, NASA GLC, risk zones).

    Runs in a background thread after startup so the API stays responsive.
    Every step is guarded by table-emptiness and skips gracefully on failure.
    """
    db = SessionLocal()
    try:
        ensure_roles(db)
        state_objs, district_objs, villages = ensure_geo(db)
        seed_terrain(db, district_objs, villages)
        seed_power_environment(db, district_objs)
        seed_landslides(db, district_objs)
        seed_risk_zones(db, district_objs, villages)
        print("Real-data fill complete.")
    except Exception:
        import traceback

        traceback.print_exc()
    finally:
        db.close()


def run_seed():
    """Compatibility entry point: migration + full real-data fill."""
    run_migration()
    run_real_data_fill()


if __name__ == "__main__":
    run_seed()