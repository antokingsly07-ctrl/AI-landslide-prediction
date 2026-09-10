"""Seed realistic demo data for North-Eastern Indian states/districts.

All data is clearly simulated for demonstration purposes only. It is never
presented as live government data in the UI.
"""
import json
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

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
    EmergencyResponse,
    FieldReport,
    Incident,
    RiskPrediction,
    RiskZone,
    Road,
)


def utcnow():
    return datetime.now(timezone.utc)


# North East states with real districts (with approx centroids)
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

SANDBOX_USER_CREDENTIALS = {
    "super_admin@landslide.demo": ("Super Admin", "admin123", "super_admin", None),
    "district@landslide.demo": ("District Admin", "district123", "district_admin", "Aizawl"),
    "disaster@landslide.demo": ("Disaster Mgmt", "disaster123", "disaster_mgmt", None),
    "field@landslide.demo": ("Field Official", "field123", "field_official", "East Khasi Hills"),
    "citizen@landslide.demo": ("Citizen", "citizen123", "citizen", None),
}

VILLAGE_NAMES = [
    "Zokhawsang", "Mawphlang", "Cherrapunjee", "Sohra", "Laitmawsiang",
    "Umiam", "Shillong Peak", "Laitlyngkot", "Mawsynram", "Pynursla",
    "Dawki", "Amlaren", "Champhai", "Lunglei Town", "Serchhip",
    "Thenzawl", "Hmunsang", "Kolasib", "Chamring", "Vairengte",
]

ROAD_SUFFIXES = ["National Highway", "State Highway", "District Road", "Village Road", "Border Road"]

INFRA_TYPES = ["hospital", "school", "emergency_service", "bridge", "power_station"]


def seed(db: Session):
    # Roles
    roles = {}
    for name, desc in ROLES:
        obj = db.scalar(select(Role).where(Role.name == name))
        if not obj:
            obj = Role(name=name, description=desc)
            db.add(obj)
        roles[name] = obj
    db.commit()

    # States + districts + villages + roads + infra + sensors
    state_objs = {}
    district_objs = {}
    all_villages = []
    all_roads = []
    rng = random.Random(42)

    for st in STATES:
        so = db.scalar(select(State).where(State.code == st["code"]))
        if not so:
            so = State(code=st["code"], name=st["name"])
            db.add(so)
            db.flush()
        state_objs[st["code"]] = so
        for d in st["districts"]:
            di = db.scalar(select(District).where(District.code == f"{st['code']}-{d['name']}"))
            if not di:
                di = District(
                    code=f"{st['code']}-{d['name']}",
                    name=d["name"],
                    state_id=so.id,
                    latitude=d["lat"],
                    longitude=d["lon"],
                    population=d["pop"],
                    risk_score=round(rng.uniform(20, 85), 1),
                )
                db.add(di)
                db.flush()
            district_objs[(st["code"], d["name"])] = di

            # villages
            for i in range(6):
                vname = rng.choice(VILLAGE_NAMES) + f" {i+1} {d['name']}"
                v = db.scalar(select(Village).where(Village.name == vname))
                if not v:
                    v = Village(
                        name=vname,
                        district_id=di.id,
                        latitude=round(d["lat"] + rng.uniform(-0.15, 0.15), 5),
                        longitude=round(d["lon"] + rng.uniform(-0.15, 0.15), 5),
                        population=rng.randint(500, 20000),
                        risk_score=round(rng.uniform(20, 90), 1),
                    )
                    db.add(v)
                    db.flush()
                all_villages.append(v)

            # roads
            if not db.scalar(select(Road).where(Road.district_id == di.id).limit(1)):
                for _j in range(4):
                    rname = f"{d['name']} {ROAD_SUFFIXES[rng.randrange(len(ROAD_SUFFIXES))]} {_j+1}"
                    r = db.scalar(select(Road).where(Road.name == rname))
                    if not r:
                        r = Road(
                            name=rname,
                            road_type=rng.choice(["highway", "state", "district", "village"]),
                            district_id=di.id,
                            latitude=round(d["lat"] + rng.uniform(-0.2, 0.2), 5),
                            longitude=round(d["lon"] + rng.uniform(-0.2, 0.2), 5),
                            status=rng.choice(["open", "open", "open", "restricted", "blocked"]),
                            population_served=rng.randint(1000, 200000),
                            alternative_route=rng.random() > 0.3,
                            priority_score=round(rng.uniform(0, 100), 1),
                    )
                    db.add(r)
                    db.flush()
                all_roads.append(r)

            # infrastructure
            for k in range(3):
                it = INFRA_TYPES[rng.randrange(len(INFRA_TYPES))]
                iname = f"{d['name']} {it.title()} {k+1}"
                if not db.scalar(select(Infrastructure).where(Infrastructure.name == iname)):
                    db.add(Infrastructure(
                        name=iname,
                        infra_type=it,
                        district_id=di.id,
                        village_id=rng.choice(all_villages).id if all_villages else None,
                        latitude=round(d["lat"] + rng.uniform(-0.1, 0.1), 5),
                        longitude=round(d["lon"] + rng.uniform(-0.1, 0.1), 5),
                        importance=rng.randint(2, 5),
                        population_served=rng.randint(500, 50000),
                    ))

            # sensors
            for stype in ["soil_moisture", "rain_gauge", "tilt", "ground_movement", "temperature"]:
                sname = f"{d['name']} {stype.replace('_', ' ').title()} Sensor"
                if not db.scalar(select(Sensor).where(Sensor.name == sname)):
                    db.add(Sensor(
                        name=sname,
                        sensor_type=stype,
                        district_id=di.id,
                        latitude=round(d["lat"] + rng.uniform(-0.12, 0.12), 5),
                        longitude=round(d["lon"] + rng.uniform(-0.12, 0.12), 5),
                        status="online",
                        api_token=f"tok_{uuid.uuid4().hex[:16]}",
                    ))
    db.commit()

    # Demo users
    users = {}
    for email, (fname, pw, role, dist) in SANDBOX_USER_CREDENTIALS.items():
        u = db.scalar(select(User).where(User.email == email))
        did = None
        if dist:
            for (code, dname), dobj in district_objs.items():
                if dname == dist:
                    did = dobj.id
                    break
        if not u:
            u = User(
                email=email,
                full_name=fname,
                hashed_password=hash_password(pw),
                role_id=roles[role].id,
                district_id=did,
                phone=f"+91 9{rng.randint(10000000, 99999999)}",
                preferred_language=rng.choice(["en", "hi", "as", "bn"]),
            )
            db.add(u)
        users[role] = u
    db.commit()

    # Timeseries environmental data over the last 7 days
    now = utcnow()
    all_districts = list(district_objs.values())
    if not db.scalar(select(RainfallRecord).limit(1)):
        for day in range(7, -1, -1):
            for di in all_districts:
                base_rain = rng.uniform(5, 60)
                rain24 = round(base_rain + rng.uniform(0, 150), 2)
                rain1 = round(base_rain * rng.uniform(0.5, 1.5), 2)
                db.add(RainfallRecord(
                    latitude=di.latitude, longitude=di.longitude, district_id=di.id,
                    amount_mm=rain24, intensity=rain1,
                    rain_1h=rain1, rain_6h=round(rain1 * rng.uniform(3, 6), 2),
                    rain_24h=rain24, rain_3d=round(rain24 * rng.uniform(2, 3.5), 2),
                    rain_7d=round(rain24 * rng.uniform(4, 6), 2),
                    observed_at=now - timedelta(days=day), is_demo=True,
                ))
                db.add(SoilMoistureRecord(
                    latitude=di.latitude, longitude=di.longitude, district_id=di.id,
                    moisture_percent=round(rng.uniform(35, 96), 1),
                    observed_at=now - timedelta(days=day),
                ))
                db.add(WeatherRecord(
                    latitude=di.latitude, longitude=di.longitude, district_id=di.id,
                    temperature_c=round(rng.uniform(18, 30), 1),
                    humidity_percent=round(rng.uniform(65, 98), 1),
                    precipitation_mm=rain24, forecast="Monsoon showers",
                ))
                db.add(TerrainData(
                    latitude=di.latitude, longitude=di.longitude, district_id=di.id,
                    slope_deg=round(rng.uniform(10, 45), 1),
                    elevation_m=round(rng.uniform(200, 1800), 1),
                    land_cover=rng.choice(["forest", "shrubland", "cropland"]),
                    distance_to_roads_m=round(rng.uniform(20, 500), 1),
                ))
        db.commit()

    # Sensor readings (latest)
    sensors = db.scalars(select(Sensor)).all()
    if not db.scalar(select(SensorReading).limit(1)):
        for s in sensors:
            n = rng.randint(3, 8)
            for i in range(n):
                val = {"soil_moisture": (40, 15), "rain_gauge": (25, 20), "tilt": (2, 3),
                       "ground_movement": (5, 8), "temperature": (24, 5)}.get(s.sensor_type, (0, 1))
                db.add(SensorReading(
                    sensor_id=s.id, reading_type=s.sensor_type,
                    value=round(max(0, rng.gauss(val[0], val[1])), 2),
                    unit={"soil_moisture": "%", "rain_gauge": "mm", "tilt": "deg",
                          "ground_movement": "mm", "temperature": "C"}.get(s.sensor_type, ""),
                    read_at=now - timedelta(hours=i),
                ))
        db.commit()

    # Historical landslides
    if not db.scalar(select(LandslideHistory).limit(1)):
        for _ in range(40):
            di = rng.choice(all_districts)
            db.add(LandslideHistory(
                latitude=di.latitude + rng.uniform(-0.1, 0.1),
                longitude=di.longitude + rng.uniform(-0.1, 0.1),
                district_id=di.id,
                severity=rng.randint(1, 5),
                cause=rng.choice(["rainfall", "rainfall", "earthquake", "human_activity"]),
                year=rng.randint(1998, 2025),
                occurred_on=now - timedelta(days=rng.randint(30, 9000)),
            ))
        db.commit()

    # Risk zones
    if not db.scalar(select(RiskZone).limit(1)):
        for v in all_villages[:60]:
            score = round(rng.uniform(15, 95), 1)
            db.add(RiskZone(
                name=v.name + " Zone",
                risk_score=score,
                risk_level=("CRITICAL" if score >= 81 else "HIGH" if score >= 61
                            else "MODERATE" if score >= 41 else "LOW" if score >= 21 else "VERY_LOW"),
                latitude=v.latitude, longitude=v.longitude,
                district_id=v.district_id, village_id=v.id,
                population=v.population, area_km2=round(rng.uniform(0.5, 8), 2),
            ))
        db.commit()

    # Risk predictions history
    if not db.scalar(select(RiskPrediction).limit(1)):
        for _ in range(25):
            di = rng.choice(all_districts)
            score = round(rng.uniform(20, 95), 1)
            db.add(RiskPrediction(
                latitude=di.latitude, longitude=di.longitude, district_id=di.id,
                risk_score=score,
                risk_level=("CRITICAL" if score >= 81 else "HIGH" if score >= 61 else "MODERATE" if score >= 41 else "LOW"),
                confidence=round(rng.uniform(0.6, 0.95), 2),
                factors=json.dumps(["Heavy rainfall", "High soil moisture", "Steep slope"]),
                factor_contributions=json.dumps([
                    {"factor": "Heavy 24-hour rainfall", "contribution": 25},
                    {"factor": "High soil moisture", "contribution": 20},
                ]),
                recommended_action="Increased monitoring recommended",
                predicted_at=now - timedelta(hours=rng.randint(0, 48)),
            ))
        db.commit()

    # Top-up fresh telemetry so the 7-day dashboard trends never go stale
    # on demo deployments (seed may have run days ago).
    last_rain = db.scalar(select(func.max(RainfallRecord.observed_at)))
    if last_rain is None or (now - last_rain) > timedelta(hours=18):
        for day in (0, 1):
            for di in all_districts:
                base_rain = rng.uniform(5, 60)
                rain24 = round(base_rain + rng.uniform(0, 120), 2)
                rain1 = round(base_rain * rng.uniform(0.5, 1.5), 2)
                db.add(RainfallRecord(
                    latitude=di.latitude, longitude=di.longitude, district_id=di.id,
                    amount_mm=rain24, intensity=rain1,
                    rain_1h=rain1, rain_6h=round(rain1 * rng.uniform(3, 6), 2),
                    rain_24h=rain24, rain_3d=round(rain24 * rng.uniform(2, 3.5), 2),
                    rain_7d=round(rain24 * rng.uniform(4, 6), 2),
                    observed_at=now - timedelta(days=day), is_demo=True,
                ))
                db.add(SoilMoistureRecord(
                    latitude=di.latitude, longitude=di.longitude, district_id=di.id,
                    moisture_percent=round(rng.uniform(35, 96), 1),
                    observed_at=now - timedelta(days=day),
                ))
        db.commit()

    last_pred = db.scalar(select(func.max(RiskPrediction.predicted_at)))
    if last_pred is None or (now - last_pred) > timedelta(hours=18):
        for _ in range(4):
            di = rng.choice(all_districts)
            score = round(rng.uniform(20, 95), 1)
            db.add(RiskPrediction(
                latitude=di.latitude, longitude=di.longitude, district_id=di.id,
                risk_score=score,
                risk_level=("CRITICAL" if score >= 81 else "HIGH" if score >= 61 else "MODERATE" if score >= 41 else "LOW"),
                confidence=round(rng.uniform(0.6, 0.95), 2),
                factors=json.dumps(["Heavy rainfall", "High soil moisture", "Steep slope"]),
                factor_contributions=json.dumps([
                    {"factor": "Heavy 24-hour rainfall", "contribution": 25},
                    {"factor": "High soil moisture", "contribution": 20},
                ]),
                recommended_action="Increased monitoring recommended",
                predicted_at=now - timedelta(hours=rng.randint(0, 48)),
            ))
        db.commit()

    # Incidents
    if not db.scalar(select(Incident).limit(1)):
        inc = Incident(
            incident_type="slope_crack", severity="high", status="response",
            verification_status="verified",
            description="Large cracks observed near hillside road leading to village.",
            latitude=24.81, longitude=92.80, district_id=district_objs[("AS", "Cachar")].id,
            reported_by=users["field_official"].id,
        )
        db.add(inc)
        db.flush()
        db.add(EmergencyResponse(
            incident_id=inc.id,
            priority_score=88.0,
            priority_class="immediate",
            population_affected=12500,
        ))
        inc2 = Incident(
            incident_type="blocked_road", severity="critical", status="monitoring",
            verification_status="verified",
            description="Amlaren road fully blocked by landslide debris.",
            latitude=25.57, longitude=91.88, district_id=district_objs[("ML", "East Khasi Hills")].id,
            reported_by=users["citizen"].id,
        )
        db.add(inc2)
        db.flush()
        db.add(EmergencyResponse(
            incident_id=inc2.id,
            priority_score=82.0,
            priority_class="high",
            population_affected=8900,
        ))
        db.commit()

    # Field reports tied to incidents
    if not db.scalar(select(FieldReport).limit(1)):
        db.add(FieldReport(
            report_type="slope_crack", severity="high",
            description="Crack widening along NH-6 section.",
            latitude=24.81, longitude=92.80, district_id=district_objs[("AS", "Cachar")].id,
            reported_by=users["field_official"].id,
            incident_id=db.scalar(select(Incident).where(Incident.incident_type == "slope_crack").limit(1)).id,
            sync_status="synced",
        ))
        db.commit()

    # Alerts
    if not db.scalar(select(Alert).limit(1)):
        db.add(Alert(
            title="Landslide Risk Warning: High",
            message="A High landslide risk has been detected near Cachar (78/100). Increased monitoring recommended.",
            severity="warning", alert_type="risk", status="active", risk_level="HIGH",
            cause="AI risk prediction exceeded threshold",
            recommended_action="Increased monitoring and preparedness",
            district_id=district_objs[("AS", "Cachar")].id,
            latitude=24.81, longitude=92.80,
            affected_villages=json.dumps(["Village 1 Cachar", "Village 2 Cachar"]),
            affected_roads=json.dumps(["NH-6"]),
        ))
        db.commit()

    print("Seed complete.")

    # assign users to global dict for emergencies
    db.commit()


def run_seed():
    db = SessionLocal()
    try:
        seed(db)
        seed_example_data(db)
    except Exception:
        import traceback

        traceback.print_exc()
        raise
    finally:
        db.close()


def ensure_admin_login() -> None:
    """Guarantee the demo super admin can log in, independently of the heavy
    demo seed (which can abort part-way on a fresh Postgres and skip users)."""
    from app.db.session import SessionLocal as _SL

    db = _SL()
    try:
        role = db.scalar(select(Role).where(Role.name == "super_admin"))
        if role is None:
            role = Role(name="super_admin", description="Platform administrator with full access")
            db.add(role)
            db.commit()
        user = db.scalar(select(User).where(User.email == "super_admin@landslide.demo"))
        if user is None:
            db.add(User(
                email="super_admin@landslide.demo",
                full_name="Super Admin",
                hashed_password=hash_password("admin123"),
                role_id=role.id,
                preferred_language="en",
            ))
            db.commit()
            print("Ensured demo super_admin login (super_admin@landslide.demo / admin123)")
    except Exception as exc:  # pragma: no cover
        print(f"Ensure admin login skipped: {exc}")
    finally:
        db.close()


def ensure_demo_users() -> None:
    """Guarantee every demo sandbox user can log in, independently of the heavy
    demo seed (which can abort part-way on a fresh Postgres and skip users).

    This is the safety net that keeps all five roles usable even when the full
    seed fails after roles are committed but before users are created.
    """
    from app.db.session import SessionLocal as _SL

    db = _SL()
    try:
        roles = {}
        for name, desc in ROLES:
            role = db.scalar(select(Role).where(Role.name == name))
            if role is None:
                role = Role(name=name, description=desc)
                db.add(role)
                db.flush()
            roles[name] = role

        districts = {d.name: d for d in db.scalars(select(District)).all()}
        for email, (fname, pw, role, dist_name) in SANDBOX_USER_CREDENTIALS.items():
            if db.scalar(select(User).where(User.email == email)):
                continue
            dist = districts.get(dist_name) if dist_name else None
            db.add(User(
                email=email,
                full_name=fname,
                hashed_password=hash_password(pw),
                role_id=roles[role].id,
                district_id=dist.id if dist else None,
                preferred_language="en",
            ))
        db.commit()
        print("Ensured demo sandbox users (all roles)")
    except Exception as exc:  # pragma: no cover
        print(f"Ensure demo users skipped: {exc}")
    finally:
        db.close()


def seed_example_data(db: Session) -> None:
    """Richer, idempotent demo data for incidents, field reports, alerts,
    emergency responses and road/sensor statuses. Safe to run repeatedly.

    Uses distinct marker rows so extra data is added only if missing, without
    disturbing whatever the base seed (or a previously failed run) stored.
    """
    rng = random.Random(101)
    now = utcnow()

    def by_district(name: str):
        return db.scalar(select(District).where(District.name == name))

    def by_role(role_name: str):
        return db.scalar(
            select(User).join(Role, User.role_id == Role.id).where(Role.name == role_name).limit(1)
        )

    field = by_role("field_official")
    citizen = by_role("citizen")

    try:
        # --- Extra incidents + emergency responses -------------------------
        incidents_extra = [
            ("rockfall", "medium", "reported", "pending", "Dima Hasao", "citizen",
             "Rockfall along the hill section of NH-6 after overnight rain; loose boulders on shoulder."),
            ("movement", "critical", "response", "verified", "Aizawl", "field",
             "Rapid ground movement detected at Chalfilh village boundary; cracks visible across road."),
            ("blocked_road", "high", "monitoring", "verified", "East Khasi Hills", "field",
             "Shillong-Cherrapunjee road partially blocked by boulders and mud."),
            ("sinkhole", "medium", "reported", "pending", "Ri Bhoi", "citizen",
             "Sinkhole forming near new bridge construction site; surface depression growing."),
            ("slope_crack", "high", "response", "verified", "Gomati", "citizen",
             "Longitudinal cracks widening on a residential slope above the bazaar."),
            ("flooding", "critical", "response", "verified", "Cachar", "field",
             "Waterlogging undercutting hill roads in low-lying wards after sustained rain."),
        ]
        added_incidents = 0
        for itype, sev, status, vstatus, dname, by, desc in incidents_extra:
            if db.scalar(select(Incident).where(Incident.description == desc)):
                continue
            di = by_district(dname)
            if di is None:
                continue
            reporter = field if by == "field" else citizen
            inc = Incident(
                incident_type=itype, severity=sev, status=status,
                verification_status=vstatus, description=desc,
                latitude=di.latitude + rng.uniform(-0.08, 0.08),
                longitude=di.longitude + rng.uniform(-0.08, 0.08),
                district_id=di.id, reported_by=reporter.id if reporter else None,
                reported_at=now - timedelta(hours=rng.randint(1, 72)),
                resolved_at=(now - timedelta(hours=rng.randint(2, 24))) if status == "monitoring" else None,
            )
            db.add(inc)
            db.flush()
            score = {"critical": rng.uniform(80, 96), "high": rng.uniform(65, 82),
                     "medium": rng.uniform(45, 64), "low": rng.uniform(20, 44)}.get(sev, 50)
            cls = "immediate" if score >= 85 else "high" if score >= 65 else "medium" if score >= 45 else "low"
            db.add(EmergencyResponse(
                incident_id=inc.id,
                priority_score=round(score, 1),
                priority_class=cls,
                population_affected=int(rng.uniform(800, 18000)),
                status=("ongoing" if status == "response" else "planned"),
                responder_notes=f"Team routed to {dname}; Evacuation buffer approved for {cls} priority.",
            ))
            added_incidents += 1
        db.commit()
        if added_incidents:
            print(f"Added {added_incidents} example incidents + emergency responses.")

        # --- Extra field reports ------------------------------------------
        reports_extra = [
            ("rockfall", "medium", "Boulder deposition measured on NH-6 shoulder near Dima Hasao.", "Dima Hasao", "field"),
            ("blocked_road", "high", "Debris piled 1.5 m deep across road; detour via village track.", "East Khasi Hills", "field"),
            ("slope_crack", "high", "Crack aperture ~120 mm and extending 40 m along slope.", "Gomati", "field"),
            ("flooding", "critical", "Sewage + runoff flooding hillside; structures at risk.", "Cachar", "citizen"),
            ("movement", "critical", "Tiltmeter spikes recorded; staff instructed to blank surveillance.", "Aizawl", "field"),
        ]
        added_reports = 0
        for rtype, sev, desc, dname, by in reports_extra:
            if db.scalar(select(FieldReport).where(FieldReport.description == desc)):
                continue
            di = by_district(dname)
            if di is None:
                continue
            reporter = field if by == "field" else citizen
            db.add(FieldReport(
                report_type=rtype, severity=sev, description=desc,
                latitude=di.latitude + rng.uniform(-0.05, 0.05),
                longitude=di.longitude + rng.uniform(-0.05, 0.05),
                district_id=di.id,
                reported_by=reporter.id if reporter else None,
                reported_at=now - timedelta(hours=rng.randint(1, 48)),
                sync_status="synced",
            ))
            added_reports += 1
        db.commit()
        if added_reports:
            print(f"Added {added_reports} example field reports.")

        # --- Extra alerts -----------------------------------------------------
        alerts_extra = [
            ("Extreme Rainfall Watch: Dima Hasao", "watch", "rainfall", "active", "HIGH",
             "Dima Hasao", "Extreme 24-hour rainfall (210 mm) forecast overnight.",
             "Move vulnerable families away from steep slopes; check early-warning siren.", ["NH-6"]),
            ("Critical: Elevated Rockfall Risk after Tremor", "critical", "risk", "active", "CRITICAL",
             "Aizawl", "Post-tremor slope shaking increases rockfall probability.",
             "Restrict non-essential road use; dispatch inspection teams.", []),
            ("Soil Moisture Anomaly: Ri Bhoi", "advisory", "soil", "acknowledged", "MODERATE",
             "Ri Bhoi", "Soil moisture above seasonal norms in northern catchment.",
             "Continue weekly monitoring cadence.", []),
            ("Road Closure Advisory: NH-6 Section", "warning", "road", "active", "HIGH",
             "Dima Hasao", "Rockfall debris reduces NH-6 to single lane near km 42.",
             "Flag closure; deploy traffic control.", ["NH-6"]),
            ("Satellite Deformation Signal Resolved: Cachar", "warning", "satellite", "resolved", "HIGH",
             "Cachar", "Interferometric signal reduced to background after field inspection.",
             "Archive observation; keep zone under watch.", []),
        ]
        added_alerts = 0
        for title, sev, atype, status, rlevel, dname, msg, action, roads in alerts_extra:
            if db.scalar(select(Alert).where(Alert.title == title)):
                continue
            di = by_district(dname)
            if di is None:
                continue
            db.add(Alert(
                title=title, message=msg, severity=sev, alert_type=atype, status=status,
                risk_level=rlevel, cause="Auto-generated from demo enrichment seed",
                recommended_action=action,
                affected_villages=json.dumps([v.name for v in (di.villages or [])[:2]]),
                affected_roads=json.dumps(roads),
                district_id=di.id,
                latitude=di.latitude + rng.uniform(-0.1, 0.1),
                longitude=di.longitude + rng.uniform(-0.1, 0.1),
                triggered_at=now - timedelta(hours=rng.randint(2, 48)),
            ))
            added_alerts += 1
        db.commit()
        if added_alerts:
            print(f"Added {added_alerts} example alerts.")

        # --- Road statuses (only if all roads are currently 'open') -------------
        if not db.scalar(select(Road).where(Road.status.in_(["blocked", "restricted", "severely_blocked"]))):
            roads = db.scalars(select(Road).limit(8)).all()
            for i, rd in enumerate(roads):
                rd.status = ["blocked", "restricted", "severely_blocked", "restricted"][i % 4]
                rd.priority_score = round(rng.uniform(65, 95), 1)
                rd.alternative_route = i % 3 != 0
                rd.last_status_update = now - timedelta(hours=rng.randint(1, 30))
            db.commit()
            print(f"Marked {len(roads)} example roads as affected.")

        # --- Sensor status variety (only if every sensor is 'online') -----------
        if not db.scalar(select(Sensor).where(Sensor.status != "online")):
            offline = db.scalars(select(Sensor).limit(5)).all()
            for j, s in enumerate(offline):
                s.status = "maintenance" if j < 2 else "offline"
            db.commit()
            print("Set example sensor statuses (maintenance/offline).")

    except Exception as exc:  # pragma: no cover
        import traceback

        traceback.print_exc()
        print(f"Example-data enrichment skipped: {exc}")
        try:
            db.rollback()
        except Exception:
            pass


if __name__ == "__main__":
    run_seed()
