from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any
import time
import logging

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Dataset, DatasetColumn, IngestionRun

logger = logging.getLogger("insightsentinel")

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/csv")
async def ingest_csv(
    dataset_name: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    started_wall = datetime.now(timezone.utc)
    started_mono = time.monotonic()

    # STEP 0: read file
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    # STEP 1: parse CSV
    try:
        df = pd.read_csv(BytesIO(raw))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {type(e).__name__}: {e}")

    if df.shape[1] == 0:
        raise HTTPException(status_code=400, detail="CSV has no columns")

    row_count = int(df.shape[0])
    column_count = int(df.shape[1])

    # STEP 2: create dataset
    dataset = Dataset(
        name=dataset_name,
        description=description,
        row_count=row_count,
        column_count=column_count,
    )
    db.add(dataset)
    db.flush()  # dataset.id available

    # STEP 3: create run (persist early so failures still get recorded)
    run = IngestionRun(
        dataset_id=dataset.id,
        status="created",
        message="Ingestion created",
        started_at=started_wall,
    )
    db.add(run)
    db.commit()
    db.refresh(dataset)
    db.refresh(run)

    # STEP 4+: profiling lifecycle
    try:
        # move to profiling
        run.status = "profiling"
        run.message = "Profiling started"
        db.add(run)
        db.commit()
        db.refresh(run)

        # create dataset columns
        for col in df.columns:
            s = df[col]
            null_count = int(s.isna().sum())
            distinct_count = int(s.dropna().astype(str).nunique())

            db.add(
                DatasetColumn(
                    dataset_id=dataset.id,
                    name=str(col),
                    dtype=str(s.dtype),
                    null_count=null_count,
                    distinct_count=distinct_count,
                )
            )

        # finalize
        finished_wall = datetime.now(timezone.utc)
        duration_ms = int((time.monotonic() - started_mono) * 1000)

        run.status = "completed"
        run.message = "Ingestion completed successfully"
        run.completed_at = finished_wall
        run.duration_ms = duration_ms
        run.error_message = None

        db.add(run)
        db.commit()
        db.refresh(run)

        return {
            "dataset_id": str(dataset.id),
            "run_id": str(run.id),
            "name": dataset.name,
            "description": dataset.description,
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
            "status": run.status,
            "message": run.message,
            "duration_ms": run.duration_ms,
        }

    except Exception as e:
        logger.exception("Ingestion failed")

        finished_wall = datetime.now(timezone.utc)
        duration_ms = int((time.monotonic() - started_mono) * 1000)

        # best-effort: record failure
        run.status = "failed"
        run.message = "Ingestion failed"
        run.error_message = f"{type(e).__name__}: {e}"
        run.completed_at = finished_wall
        run.duration_ms = duration_ms

        db.add(run)
        db.commit()

        raise HTTPException(status_code=500, detail=f"Ingestion failed: {type(e).__name__}: {e}")