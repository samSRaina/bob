"""FastAPI application entrypoint: CORS, REST routers, startup DB init."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_rest import router as rest_router
from app.core.config import get_settings
from app.core.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("bob_engine.main")

settings = get_settings()

app = FastAPI(
    title="Bob Engine — FIR Intelligence & Crime Pattern Detector",
    description=(
        "Ingests digitized FIRs, resolves repeat offenders and criminal syndicates "
        "across police-station and district boundaries, and serves an RBAC-scoped "
        "crime-intelligence dashboard. IBM Bob is used exclusively as the FIR "
        "extraction copilot; every other engine is deterministic."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rest_router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info("Bob Engine started. bob_configured=%s", settings.bob_configured)
