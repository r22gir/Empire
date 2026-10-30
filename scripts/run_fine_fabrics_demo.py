#!/usr/bin/env python3
"""Local Empire Fine Fabrics demo (mock catalog, test-mode checkout).

Does not load the full Empire backend. Seeded from the bundled example CSV.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("EMPIRE_TASK_DB", str(Path("/tmp/empire_fine_fabrics_demo.db")))
os.environ.setdefault("EMPIRE_DB_PATH", os.environ["EMPIRE_TASK_DB"])
os.environ.setdefault("FINE_FABRICS_PHOTOS_DIR", "/tmp/empire_fine_fabrics_photos")
os.environ["FINE_FABRICS_SEED_DEMO"] = "1"
os.environ.setdefault("STRIPE_SECRET_KEY", "")

import sys

sys.path.insert(0, str(ROOT / "backend"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.fine_fabrics import router, seed_demo_catalog

app = FastAPI(title="Empire Fine Fabrics demo")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1")
seed_demo_catalog()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
