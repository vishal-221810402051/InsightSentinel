from __future__ import annotations

import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.dataset import Dataset
from app.models.dataset_risk_history import DatasetRiskHistory
from app.services.alert_engine import evaluate_dataset_rules
from app.services.pg_lock import advisory_unlock, try_advisory_lock
from app.services.risk_engine import _get_latest_signal_timestamp, track_dataset_risk

logger = logging.getLogger("insightsentinel.scheduler")

_scheduler: BackgroundScheduler | None = None
LOCK_KEY = "insightsentinel:scheduler:v1"


def _scheduler_job():
    start = time.time()
    settings = get_settings()
    logger.info("Scheduler tick started")

    db: Session = SessionLocal()
    total_datasets = 0
    processed = 0
    failures = 0
    skipped_no_change = 0
    alerts_created_total = 0
    risk_tracked_total = 0

    try:
        if not try_advisory_lock(db, LOCK_KEY):
            logger.info("Scheduler lock not acquired - skipping tick.")
            return

        logger.info("Scheduler leader lock acquired.")

        datasets = db.query(Dataset).all()
        total_datasets = len(datasets)

        for ds in datasets:
            try:
                if not ds.row_count or ds.row_count == 0:
                    continue

                latest_signal = _get_latest_signal_timestamp(db, ds.id)
                latest_risk = (
                    db.query(DatasetRiskHistory.created_at)
                    .filter(DatasetRiskHistory.dataset_id == ds.id)
                    .order_by(DatasetRiskHistory.created_at.desc())
                    .limit(1)
                    .scalar()
                )
                if latest_risk and (latest_signal is None or latest_signal <= latest_risk):
                    skipped_no_change += 1
                    logger.info("Skipping dataset (no change)", extra={"dataset_id": str(ds.id)})
                    continue

                processed += 1
                summary = evaluate_dataset_rules(db, ds.id)
                alerts_created_total += int(summary.created_events)

                risk = track_dataset_risk(db, ds.id)
                if risk and not (isinstance(risk, dict) and risk.get("skipped") is True):
                    risk_tracked_total += 1
            except Exception as e:
                failures += 1
                logger.exception(
                    "Scheduler dataset failure",
                    extra={"dataset_id": str(ds.id), "error": str(e)},
                )
    finally:
        try:
            advisory_unlock(db, LOCK_KEY)
        except Exception:
            pass
        db.close()

    duration = round((time.time() - start) * 1000, 2)
    logger.info(
        "Scheduler tick finished",
        extra={
            "datasets_total": total_datasets,
            "datasets_processed": processed,
            "datasets_skipped_no_change": skipped_no_change,
            "failures": failures,
            "alerts_created_total": alerts_created_total,
            "risk_tracked_total": risk_tracked_total,
            "duration_ms": duration,
        },
    )


def start_scheduler():
    global _scheduler
    settings = get_settings()

    if not settings.enable_scheduler:
        logger.info("Scheduler disabled via config")
        return

    if _scheduler is not None:
        logger.warning("Scheduler already started")
        return

    interval = settings.scheduler_interval_minutes
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(_scheduler_job, "interval", minutes=interval)
    _scheduler.start()

    logger.info(f"Scheduler started (interval={interval} minutes)")


def shutdown_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")
