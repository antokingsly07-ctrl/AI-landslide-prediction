# AI Landslide Early Warning & Monitoring Platform

A production-oriented AI early-warning and monitoring platform for landslides in North-Eastern India. It combines an ML risk engine, GIS mapping, real-time sensor/weather monitoring, field reporting with offline synchronization, alerts, and multilingual support.

> ⚠️ **Advisory only.** AI predictions are advisory and support — not replace — human verification and official disaster-management decisions.

## Local URLs

| Service | URL |
| --- | --- |
| **Frontend (web app)** | http://localhost:5173 |
| **Backend API** | http://127.0.0.1:8000 |
| **API Docs (Swagger UI)** | http://127.0.0.1:8000/docs |

*Start both services (see [Getting Started](#getting-started)), then open http://localhost:5173. The frontend proxies `/api` to the backend automatically.*

## Features

- **ML risk engine** — XGBoost/gradient-boosting model (explainable: rainfall, soil moisture, geology, prior landslides) producing a 0–100 risk score and level (Very Low → Critical).
- **Executive dashboard** — KPIs and charts: rainfall, soil moisture, risk trend, district risk, road connectivity, alerts, incidents.
- **GIS risk map** — Leaflet map with risk zones, incidents, blocked roads, and sensors.
- **Field reporting** — offline-first reports with photo capture, geolocation, and client-id deduplicated offline sync (PWA + IndexedDB).
- **Alerts & notifications** — multilingual verified templates (EN/HI/AS/BN/TA), SMS/Email/Push/InApp providers (mocked in demo).
- **Sensors & weather** — sensor readings with anomaly detection; pluggable IMD/weather and satellite providers (mocked in demo).
- **Role-based access** — Super Admin, District Admin, Disaster Mgmt, Field Officer, Citizen.
- **Emergency priorities** — automated incident prioritization for response teams.

## Tech Stack

- **Backend**: Python · FastAPI · SQLAlchemy · Pydantic v2 · JWT
- **ML**: scikit-learn · XGBoost · joblib
- **Frontend**: React 18 · TypeScript · Vite · Tailwind CSS · Leaflet · Recharts · i18next · PWA
- **Database**: PostgreSQL/PostGIS-ready (SQLite fallback for dev/demo)
- **Testing**: pytest (backend), Vitest (frontend)
- **Deployment**: Docker / Docker Compose

## Repository Layout

```
backend/     FastAPI application (API, services, ML, models, seed)
frontend/    React + TypeScript + Vite application
ml/          ML pipeline resources
database/    migrations + seed scripts
docs/        documentation
docker/      Docker / deployment config
scripts/     utility scripts
tests/       automated tests
```

## Getting Started

### Backend

```bash
cd backend
python -m venv .venv                 # or use an existing venv
pip install -r requirements.txt
cp ../.env.example ../.env           # set DATABASE_URL, JWT_SECRET, etc.

# Seed demo data + ensure a trained model exists:
python -c "import app.main"          # startup runs init_db, seed, and model ensure
# Or seed explicitly:
python -m app.ml.train               # train/refresh the ML model
uvicorn app.main:app --reload --port 8000
```

Demo users (see `database/seed/seed_db.py`) — e.g. `super_admin@landslide.demo` / `admin123`.

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api to :8000)
```

### Tests

```bash
# Backend
cd backend && pytest ../tests -q
# Frontend
cd frontend && npm test
```

## Configuration

Copy `.env.example` to `.env` and fill in your values. All external providers (IMD weather, satellite, SMS) have **mock** implementations by default so the app runs without API keys. Secrets are never hardcoded.

## Disclaimer

This platform is a demonstration/advisory tool. It is **not** a substitute for official geological surveys, disaster-management agencies, or emergency services. Predictions should always be verified by qualified professionals before acting.
