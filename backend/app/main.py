from __future__ import annotations

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.routes.datasets import router as datasets_router
from app.api.routes.ingest import router as ingest_router
from app.api.routes.insights import router as insights_router
from app.api.routes.runs import router as runs_router
from app.api.routes.alerts import router as alerts_router
from app.api.routes.alerts_eval import router as alerts_eval_router
from app.api.routes.alerts_suggest import router as alerts_suggest_router
from app.api.routes.anomalies import router as anomalies_router
from app.api.routes.health import router as health_router
from app.api.routes.portfolio import router as portfolio_router
from app.api.routes.risk import router as risk_router
from app.services.scheduler import start_scheduler, shutdown_scheduler

settings = get_settings()
setup_logging(settings.log_level)

logger = logging.getLogger("insightsentinel")

app = FastAPI(
    title="InsightSentinel AI",
    version="0.2.0",
    description="AI-Powered Business Data Monitoring & Decision Engine (V1)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets_router)
app.include_router(ingest_router)
app.include_router(insights_router)
app.include_router(runs_router, prefix="/runs", tags=["runs"])
app.include_router(alerts_router)
app.include_router(alerts_eval_router)
app.include_router(alerts_suggest_router)
app.include_router(anomalies_router)
app.include_router(health_router)
app.include_router(portfolio_router)
app.include_router(risk_router)


@app.on_event("startup")
def on_startup():
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    shutdown_scheduler()


@app.get("/health")
def health() -> dict[str, str]:
    logger.info("Health check requested")
    return {"status": "ok"}
