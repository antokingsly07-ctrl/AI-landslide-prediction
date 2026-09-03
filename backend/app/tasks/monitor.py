"""Real-time risk monitoring background task.

Periodically fetches weather, processes sensor/satellite data and updates risk
calculations + alerts. Runs in a background thread via FastAPI startup.
"""
import asyncio
import time


class RiskMonitor:
    def __init__(self, interval_seconds: int = 300):
        self.interval = interval_seconds
        self.running = False
        self.last_sync = None

    async def run_cycle(self, db):
        from app.services.prediction_service import evaluate_auto_alerts, check_rainfall_alert

        try:
            created = evaluate_auto_alerts(db)
            check_rainfall_alert(db)
            self.last_sync = time.time()
        except Exception as e:
            print(f"Monitor cycle error: {e}")

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

    def start(self):
        asyncio.create_task(self.loop())


monitor = RiskMonitor()
