"""
UNMAPPED — FastAPI application entry point

Startup:
    ACTIVE_COUNTRY=ghana uvicorn backend.main:app --reload
    ACTIVE_COUNTRY=bangladesh uvicorn backend.main:app --reload
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config_loader import get_config
from backend.models.db import init_db
from backend.api.skills import router as skills_router
from backend.api.readiness import router as readiness_router

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
    await init_db()
    logger.info("Database initialized")
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


from fastapi.staticfiles import StaticFiles
from pathlib import Path

app.include_router(skills_router, prefix="/skills", tags=["skills"])
app.include_router(readiness_router, prefix="/readiness", tags=["readiness"])

# Serve the Telegram Web App files
_WEBAPP_DIR = Path(__file__).parent.parent / "telegram_bot" / "webapp"
if _WEBAPP_DIR.exists():
    app.mount("/webapp", StaticFiles(directory=str(_WEBAPP_DIR), html=True), name="webapp")


@app.get("/passport/{passport_uuid}")
async def passport_webapp(passport_uuid: str):
    """Redirect to the Telegram Web App passport view."""
    from fastapi.responses import HTMLResponse
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UNMAPPED Skills Passport</title>
<script>
  // Load passport data and redirect to the full webapp
  window.location = '/webapp/passport.html?id={passport_uuid}';
</script>
</head>
<body><p>Loading your Skills Passport...</p></body>
</html>"""
    return HTMLResponse(html)
