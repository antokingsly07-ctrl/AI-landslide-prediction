"""Real-time risk monitoring background task.

Periodically fetches weather, processes sensor/satellite data and updates risk
calculations + alerts. Runs in a background thread via FastAPI startup.
"""
import asyncio
import time

from app.core.config import settings


class RiskMonitor:
    def __init__(self, interval_seconds: int | None = None):
        self.interval = interval_seconds or settings.POLL_INTERVAL_SECONDS
        self.running = False
        self.last_sync = None

    async def run_cycle(self, db):
        from app.services.prediction_service import evaluate_auto_alerts, check_rainfall_alert

        try:
            created = evaluate_auto_alerts(db)
            check_rainfall_alert(db)
            # Also re-evaluate open sensor/road alerts from recent data once an hour
            self.last_sync = time.time()
            return len(created)
        except Exception as e:
            print(f"Monitor cycle error: {e}")
            return 0

    async def loop(self):
        from app.db.session import SessionLocal

        self.running = True
        while self.running:
            db = SessionLocal()
            try:
                await self.run_cycle(db)
            finally:
                db.close()
            await asyncio.sleep(self.interval)

    def start(self) -> asyncio.Task | None:
        try:
            return asyncio.create_task(self.loop())
        except RuntimeError:
            # No running event loop yet (e.g. import-time); startup will call start()
            return None


monitor = RiskMonitor()
