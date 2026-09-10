"""API integration tests: auth, health, prediction, and registration hardening."""
import pytest


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_only_public_roles(client):
    r = client.post("/api/v1/auth/register", json={
        "email": "attacker@example.com",
        "full_name": "Attacker",
        "phone": "5551112222",
        "password": "pass1234",
        "role": "super_admin",
    })
    assert r.status_code == 403
    assert "Self-registration" in r.json()["detail"]


def test_register_and_login(client):
    r = client.post("/api/v1/auth/register", json={
        "email": "citizen@example.com",
        "full_name": "Citizen One",
        "phone": "5551234567",
        "password": "pass1234",
        "role": "citizen",
    })
    assert r.status_code == 201
    token = r.json()["access_token"]

    lr = client.post("/api/v1/auth/login", json={
        "email": "citizen@example.com",
        "password": "pass1234",
    })
    assert lr.status_code == 200
    assert lr.json()["user"]["role"] == "citizen"

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "citizen@example.com"


def test_login_wrong_password(client):
    r = client.post("/api/v1/auth/login", json={
        "email": "citizen@example.com",
        "password": "wrong-pass",
    })
    assert r.status_code == 401


def test_prediction_requires_auth(client):
    r = client.post("/api/v1/predictions", json={
        "latitude": 26.1, "longitude": 92.9,
        "rainfall_24h": 150,
    })
    assert r.status_code == 401


def test_prediction_flow(client):
    reg = client.post("/api/v1/auth/register", json={
        "email": "officer@example.com",
        "full_name": "Field Officer",
        "phone": "5559998888",
        "password": "pass1234",
        "role": "field_official",
    })
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    r = client.post("/api/v1/predictions", headers=headers, json={
        "latitude": 26.12, "longitude": 92.94,
        "rainfall_24h": 180, "rainfall_6h": 60, "rainfall_1h": 18,
        "rain_3d": 300, "rain_7d": 480,
        "soil_moisture": 78, "slope_deg": 32, "elevation_m": 950,
        "historical_frequency": 3, "distance_to_roads_m": 120,
        "vegetation_change": 0.05, "deformation_mm": 12,
    })
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["risk_score"] <= 100
    assert body["risk_level"] in {"VERY_LOW", "LOW", "MODERATE", "HIGH", "CRITICAL"}
    assert body["model"]


def test_report_export_csv(client, auth_headers):
    r = client.get("/api/v1/reports/export/csv", headers=auth_headers)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert r.headers["content-disposition"].startswith("attachment")


def test_rate_limit_login(client):
    # Exceed the login limit -> 429
    statuses = []
    for i in range(12):
        r = client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "nope",
        })
        statuses.append(r.status_code)
    assert 429 in statuses