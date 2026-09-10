"""Real-time WebSocket alert broadcasting.

Connector visibility is shared with the FastAPI app via a module-level list
of connected sockets. ``broadcast_alert`` is called whenever a new alert is
created so connected dashboards update instantly without polling.
"""
import json

from fastapi import WebSocket

_subscribers: list[WebSocket] = []


def register(ws: WebSocket) -> None:
    if ws not in _subscribers:
        _subscribers.append(ws)


def unregister(ws: WebSocket) -> None:
    if ws in _subscribers:
        _subscribers.remove(ws)


def broadcast(payload: dict) -> int:
    """Send a JSON payload to all connected clients. Returns count delivered."""
    sent = 0
    stale = []
    for ws in _subscribers:
        try:
            import asyncio

            asyncio.create_task(ws.send_text(json.dumps(payload, default=str)))
            sent += 1
        except Exception:
            stale.append(ws)
    for ws in stale:
        try:
            _subscribers.remove(ws)
        except ValueError:
            pass
    return sent


def broadcast_alert(alert_meta: dict) -> int:
    return broadcast({"type": "alert.new", "alert": alert_meta})


def subscriber_count() -> int:
    return len(_subscribers)