"""Vercel entrypoint for the FastAPI framework preset.

Vercel's FastAPI preset looks for a FastAPI instance named `app` at a
recognized entrypoint (api/index.py is one). The whole application is
served as a single Vercel Function, so no ASGI-to-Lambda adapter is needed.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# `app.*` package lives under backend/, while `database.*` (seed) is at repo root.
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, ROOT)

from app.main import app  # noqa: E402