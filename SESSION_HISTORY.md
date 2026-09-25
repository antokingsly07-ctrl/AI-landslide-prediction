# AI Landslide Prediction — Session History / Handoff

> Export of the working session so it can be continued from another device.

## Project identity
- **Repo:** `github.com/antokingsly07-ctrl/AI-landslide-prediction.git` (branch `main`, auto-deploy on push)
- **Backend:** FastAPI on **Render** -> `https://ai-landslide-prediction-n4kk.onrender.com`
- **Frontend:** React PWA on **Vercel** (proxies `/api/*` + `/media/*` to Railway via `frontend/vercel.json`; no `VITE_API_URL` needed)
- **API docs:** `/docs`, `/redoc`, `/openapi.json`; API prefix `/api/v1`
- Product: AI Landslide Early Warning & Monitoring Platform for North-Eastern India (Meghalaya/Assam focus). Global map, dashboards, ML risk, news-driven incidents, field reports, roads, sensors, emergency priorities, PWA offline sync.

## Tech stack (summary)
- Backend: Python 3.11, FastAPI 0.115, Uvicorn, SQLAlchemy 2.0, Pydantic v2 + pydantic-settings, PostgreSQL (**Aiven**) via psycopg3 / SQLite (dev), python-jose HS256 JWT, passlib/bcrypt, XGBoost 2.1.3 + scikit-learn + pandas + numpy (risk model), httpx (external providers: NASA POWER, Open-Meteo/SRTM, Planetary Computer, Google News RSS/GDELT, OpenWeather/WeatherAPI/IMD).
- Frontend: React 18 + TypeScript 5.7 + Vite 6 + Tailwind 3, react-router-dom v6, zustand, axios, leaflet/react-leaflet, recharts, i18next (en/as/bn/hi/ta), vite-plugin-pwa + idb (IndexedDB offline sync), vitest.
- Key dirs: `backend/app/{api/v1/endpoints,core,db,models,services,tasks,ml}`, `database/seed/`, `frontend/src/{pages,components,store,hooks,lib}`.

## Session timeline (this session's work, oldest -> newest)
1. **Admin reseed endpoint + full seed traceback logging** (`17d03ab`, later superseded by remote rewrite).
2. **Richer demo data + idempotent seed** (`0682c46`) - later dropped when remote rewrote seed to real data.
3. **Remote diverged:** pulled 8 fresh commits (`4ca57ce..6557a79`) - Meghalaya real sensor/road networks, road lifecycle DELETE, news-driven incidents, `/predict`, null-safe color helpers, real-data seed rewrite.
4. **Mobile-only UI redesign** (pushed as `8adab89` after rebase): hamburger slide-out drawer (`md:hidden`), compact mobile header, responsive stacking on all pages, 1-col field report form, 100dvh map, mobile CSS in `index.css` (16px inputs anti-iOS-zoom). Desktop untouched. Rebased over upstream, respected remote's removal of demo-login buttons.
5. **Emergency priorities -> reasons** (`487e98e`): `priority_service.compute_priority()` now also returns `reasons`; `/dashboard/emergency/priorities` exposes `reasons/description/responder_notes`; Emergency page renders "Why this priority".
6. **Location fix** (`39b2c05`): emergency location now resolves **district name** (+ coords when present) via District join instead of "Unknown".
7. **Rainfall/soil-moisture trends no-feed fix** (`821d1b1`, latest functional change): NASA POWER env fill is now a **rolling refresh** - `seed_power_environment()` inserts only dates newer than each district's latest per-table record (idempotent), fresh districts skip network; new `NASA_REFRESH_HOURS=6` config; `RiskMonitor.run_cycle()` refreshes env series every 6h so 7-day charts never age out. Verified: double-seed adds 0, age-backfill works, throttle works, charts return in-window points.

## Full git history (main, `git log --oneline`)
```
821d1b1 Keep rainfall/soil-moisture trends fed with rolling NASA POWER refresh
39b2c05 Emergency priorities: show district name instead of Unknown
487e98e Emergency response: show reasons derived from each incident
8adab89 Mobile-only UI improvements (desktop untouched)
6557a79 Make prediction-level color helper null-safe (accept undefined)
62ae982 Fix frontend build: guard optional road prediction_level before color lookup
234ddc3 Fix road delete: purge road_status history before removing road (FK)
bae1005 Add DELETE /roads/{id} for road lifecycle management
b691455 Fix config indentation for NEWS_ROAD_STATUS_ENABLED
3ed8cda Add Meghalaya road network: news-driven live status, manual registration, landslide-blockage prediction
08e0290 Replace generic sensor batch with documented Meghalaya gov instruments (NRSC-NDMA/GSI/NEHU IoT)
4ca57ce Deploy real Meghalaya sensor network + NASA POWER-anchored telemetry, remaining real ML districts
[+ prior upstream work: news pipeline (Google RSS+GDELT), dedupe, recompute/admin endpoints, real-data migration]
```

## Current state (important - carry this over)
- `git status` shows **one uncommitted change: `frontend/src/components/Layout.tsx`** - the **mobile drawer/top-layer z-index fix** (foil Leaflet's z-400-1000):
  - drawer overlay `z-50` -> **`z-[1001]`**
  - alert-toast `z-[60]` -> **`z-[1100]`**
  - alerts dropdown `z-50` -> **`z-[1001]`**
  - Build verify (`npm run build`) + commit + push is **pending** (interrupted mid-flight).
- Untracked root `package-lock.json` - leave out of commits.
- `SESSION_HISTORY.md` (this file) is intentionally tracked.

## Local environment & workflow notes
- OS: Windows, PowerShell 5.1. Worktree: `C:\Users\user\Desktop\landslide prediction` (repo root).
- Backend venv: `backend\.venv\Scripts\python.exe`. Build system: `requirements.txt` (root = Railway/PostgreSQL incl. psycopg; `backend/requirements.txt` = dev incl. pandas; `backend/requirements-dev.txt` adds pytest/pytest-cov/alembic).
- Frontend commands (run in `frontend/`): `npm run dev`, `npm run build` (tsc -b && vite build) - always run before pushing frontend changes; `npm test` (vitest).
- Dev DB `landslide_dev.db` (local) is **stale** vs. models (`no such column: incidents.source`) - use a fresh temp SQLite DB for verification: `DATABASE_URL=sqlite:///C:/Users/user/AppData/Local/Temp/opencode/<name>.db`, then `init_db()` + `seed(db)` + `py_compile` checks.
- Backend run: `backend\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000` (from repo root, PYTHONPATH set) or via Dockerfile `python:3.11-slim` + libgomp1 on Railway.
- Rebase workflow: `git rebase origin/main`; use `GIT_EDITOR="true"` for `git rebase --continue` (else the editor hangs the session); resolve conflicts manually, keep remote's newer decisions.
- Push = auto-deploy: Vercel frontend + Render backend (Render deploys from the GitHub branch you attached). `DATABASE_URL` on Render points at **Aiven PostgreSQL** (add `sslmode=require` to the connection string; psycopg3 handles it). C: drive low - avoid heavy pip/npm installs.

## Known facts / gotchas
- New real-data seed (`database/seed/seed_db.py`, ~870 lines) creates **no incidents directly** - incidents/emergency responses enter via the news pipeline in production. Emergency page fills as those stream in.
- Real seed sources real SRTM terrain (46 rows), NASA POWER (138 env records), NASA GLC (120 events, lagging), 22-23 risk zones, 26 gov sensors, 17 Meghalaya roads. Network failures print-and-skip (daemon thread `run_real_data_fill`).
- NASA POWER currently lags ~2 days; charts show up to today-2 and refresh via monitor.
- Bootstrap super admin: `ensure_bootstrap_admin()` from `BOOTSTRAP_ADMIN_*` env (remote removed demo-login buttons).
- Real-time WebSocket `/ws/alerts` (JWT in query param); `useRealtimeAlerts` toast in Layout.

## Suggested next moves (when landing on the new device)
1. Clone repo, recreate `backend/.venv` if needed, `npm install` in `frontend/`.
2. Finish the pending **Layout.tsx z-index fix**: `cd frontend && npm run build`, commit, push.
3. If relevant again: watch **Render logs** for "Seeded ... NASA POWER environmental records" to confirm trend backfill.
4. Optional future work (discussed, not done): **Option B** - blend live sensor readings (rain_gauge/soil_moisture types) into the two trend charts for a near-real-time feed.