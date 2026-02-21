from __future__ import annotations

import logging
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.routes.datasets import router as datasets_router
from app.api.routes.ingest import router as ingest_router
from app.api.routes.runs import router as runs_router

settings = get_settings()
setup_logging(settings.log_level)

logger = logging.getLogger("insightsentinel")

app = FastAPI(
    title="InsightSentinel AI",
    version="0.2.0",
    description="AI-Powered Business Data Monitoring & Decision Engine (V1)",
)

app.include_router(datasets_router)
app.include_router(ingest_router)
app.include_router(runs_router, prefix="/runs", tags=["runs"])

@app.get("/health")
def health() -> dict[str, str]:
    logger.info("Health check requested")
    return {"status": "ok"}