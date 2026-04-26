"""
UNMAPPED — FastAPI application entry point

Startup:
    ACTIVE_COUNTRY=ghana uvicorn backend.main:app --reload
    ACTIVE_COUNTRY=bangladesh uvicorn backend.main:app --reload
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config_loader import get_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_config()
    logger.info(
        "UNMAPPED starting | country=%s (%s) | currency=%s | informal_share=%.0f%%",
        cfg.country.iso_code,
        cfg.country.name,
        cfg.country.currency,
        cfg.labor_market.informal_sector_share * 100,
    )
    yield
    logger.info("UNMAPPED shutting down")


app = FastAPI(
    title="UNMAPPED",
    description="Open Skills Infrastructure for the AI Age",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    cfg = get_config()
    return {
        "name": "UNMAPPED",
        "version": "0.1.0",
        "active_country": cfg.country.iso_code,
        "country_name": cfg.country.name,
        "currency": cfg.country.currency,
        "modules": ["skills_signal", "readiness", "matching"],
        "data_gaps_count": len(cfg.data_gaps),
    }


@app.get("/config")
async def active_config():
    """Return the active country configuration (for debugging and demo purposes)."""
    cfg = get_config()
    return cfg.model_dump()


@app.get("/health")
async def health():
    return {"status": "ok", "country": get_config().country.iso_code}


# ── Module routers (registered in later phases) ──────────────────────────────
# from backend.api.skills import router as skills_router
# from backend.api.readiness import router as readiness_router
# from backend.api.matching import router as matching_router
# app.include_router(skills_router, prefix="/skills", tags=["skills"])
# app.include_router(readiness_router, prefix="/readiness", tags=["readiness"])
# app.include_router(matching_router, prefix="/matching", tags=["matching"])
