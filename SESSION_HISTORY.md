# AI Landslide Prediction — Session History / Handoff

> Export of the working session so it can be continued from another device.

## Project identity
- **Repo:** `github.com/antokingsly07-ctrl/AI-landslide-prediction.git` (branch `main`, auto-deploy on push)
- **Backend:** FastAPI on **Render** -> `https://ai-landslide-prediction-n4kk.onrender.com`
- **DB:** PostgreSQL on **Aiven** (`DATABASE_URL` on Render env = `postgres://...`; add `sslmode=require`; psycopg3 handles it)
- **Frontend:** React PWA on **Vercel** -> `https://api-l5j34q8to-antokingsly07-ctrls-projects.vercel.app` (proxies `/api/*` + `/media/*` to the Render service via `frontend/vercel.json`; no `VITE_API_URL` needed - do NOT set it on Vercel or pages will hit a dead URL while WS toasts still work)
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
7. **Rainfall/soil-moisture trends no-feed fix** (`821d1b1`): NASA POWER env fill is now a **rolling refresh** - `seed_power_environment()` inserts only dates newer than each district's latest per-table record (idempotent), fresh districts skip network; new `NASA_REFRESH_HOURS=6` config; `RiskMonitor.run_cycle()` refreshes env series every 6h so 7-day charts never age out. Verified: double-seed adds 0, age-backfill works, throttle works, charts return in-window points.
8. **Session handoff doc** (`a853535`): created `SESSION_HISTORY.md` and pushed it so work continues from another device.
9. **Move off Railway** (`d60c439` + Render/Aiven setup): DB from Neon to **Aiven PostgreSQL**; backend to **Render**; `frontend/vercel.json` rewrites `/api/*`+`/media/*` to the new Render service. Login issue after migration was an **empty Aiven DB** (no users) - probed and created `probe@landslide.dev / TempPass123!` as first super_admin.
10. **Create-account toggle** (`8515527`): `Login.tsx` gains "Create account" self-registration (first registered user = super_admin); i18n keys already existed. User's real admin verified live: `antokingsly07@gmail.com / milkbiscuit`.
11. **Mobile drawer z-index fix** (`4e4b333`): drawer overlay + alerts dropdown `z-[1001]`, alert toast `z-[1100]` (above Leaflet's z-400-1000).
12. **Open-Meteo 429 fix** (`7b4826b`): `terrain_service.py` rewritten (global throttle, chunked `_MAX_PER_REQUEST=40`, dedupe, retry w/ backoff honoring `Retry-After`; `get_terrain_many()`); `seed_db.py::seed_terrain` one batched sweep. Verified 46/46 terrain rows, 0 nulls.
13. **News-incident geo + dashboard KPI fix** (`046dbb1`, latest): all 29 live auto-news incidents had **NULL district_id/lat/lon** (created in a first-boot race before reference geo was seeded; URL-dedupe froze them geo-less), so GIS map + dashboard KPIs were empty while WS toasts still fired. Fix adds `reconcile_news_geo()` in `news_service.py` (backfills geo for auto-news incidents missing district + syncs their `news_report` alerts on every news cycle) and `summary()` no longer excludes null-district rows from global KPIs (rfilter `true()` when no district selected). Verified locally (geo restored, alert synced, active_incidents 0->1) and live (UI now shows lists, KPIs non-zero).

## Full git history (main, `git log --oneline`)
```
046dbb1 fix: backfill geo for geo-less auto-news incidents; count unresolved rows in dashboard KPIs
748a273 trigger: rerun Render real-data deployment
7b4826b Fix Open-Meteo 429: throttle + batch terrain seeding
4e4b333 Mobile drawer/top-layer z-index fix
8515527 Add create-account toggle to login
d60c439 Switch deploy target from Railway to Render
a853535 Add session handoff doc
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
- Last push `046dbb1`; `git status` clean except the untracked root `package-lock.json` (leave out of commits).
- Live verified via Vercel proxy (frontend host) AND direct Render: `/api/v1/incidents` + `/alerts?status=active` return data; dashboard summary non-zero. Deployed frontend bundle is current (contains recent Login + z-index changes).
- Reference geo resolves news text correctly locally AND in the new backfill path. The first-boot race that geo-stripped old incidents should not recur (reference geo is seeded before the news monitor's first cycle under normal startup).
- Watch Render logs for "Backfilled geo for N auto-news incident(s)." on the first news cycle after a fresh-DB boot.
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
- Vercel proxy works (tested live through the frontend host). If backend URL ever changes, update `frontend/vercel.json` rewrites AND re-check Vercel env for a stale `VITE_API_URL`.

## Suggested next moves (when landing on the new device)
1. Clone repo, recreate `backend/.venv` if needed, `npm install` in `frontend/`.
2. **Optional (offered, not implemented):** admin delete-user/role endpoint to remove the probe admin `probe@landslide.dev` (and generally manage users).
3. Watch **Render logs** for the news-cycle backfill line to confirm geo healing on the next cycle after fresh DB boots.