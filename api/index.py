"""Vercel serverless entrypoint: FastAPI app via Mangum.

Vercel runs the Python code under `api/requirements.txt` and calls `handler`.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# `app.*` package lives under backend/, while `database.*` (seed) is at repo root.
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, ROOT)

from app.main import app as fastapi_app  # noqa: E402
from mangum import Mangum  # noqa: E402

handler = Mangum(fastapi_app)