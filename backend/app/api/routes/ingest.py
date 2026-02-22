from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any
import time
import logging
import math

import pandas as pd
from pandas.api.types import is_numeric_dtype
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.models import Dataset, DatasetColumn, IngestionRun, ColumnStatistics
from app.models.dataset_preview import DatasetPreview

from app.db.session import get_db

logger = logging.getLogger("insightsentinel")

router = APIRouter(prefix="/ingest", tags=["ingest"])
PREVIEW_ROWS = 50


def _safe_float(x: Any) -> float | None:
    """Convert numpy/pandas scalars to plain float, returning None for NaN/inf."""
    if x is None:
        return None
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def _compute_numeric_stats(s: pd.Series) -> dict[str, Any] | None:
    """
    Compute mean/std/min/max + IQR outliers for a numeric series.
    Returns None if not enough numeric data.
    """
    # Drop NaNs
    x = s.dropna()
    if x.empty:
        return None

    # Need at least 2 points for std; for outliers IQR works better with >= 4
    mean_v = _safe_float(x.mean())
    std_v = _safe_float(x.std(ddof=1)) if len(x) >= 2 else None
    min_v = _safe_float(x.min())
    max_v = _safe_float(x.max())
    skew_v = _safe_float(x.skew()) if len(x) >= 3 else None
    kurt_v = _safe_float(x.kurt()) if len(x) >= 4 else None

    outlier_count = None
    outlier_ratio = None

    if len(x) >= 4:
        q1 = _safe_float(x.quantile(0.25))
        q3 = _safe_float(x.quantile(0.75))
        if q1 is not None and q3 is not None:
            iqr = q3 - q1
            # If iqr == 0, all values essentially same -> no outliers
            if iqr > 0:
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                oc = int(((x < lower) | (x > upper)).sum())
                outlier_count = oc
                outlier_ratio = _safe_float(oc / len(x)) if len(x) > 0 else None
            else:
                outlier_count = 0
                outlier_ratio = 0.0

    return {
        "mean": mean_v,
        "std": std_v,
        "min": min_v,
        "max": max_v,
        "outlier_count": outlier_count,
        "outlier_ratio": outlier_ratio,
        "skewness": skew_v,
        "kurtosis": kurt_v,
    }


@router.post("/csv")
async def ingest_csv(
    dataset_name: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    started_wall = datetime.now(timezone.utc)
    started_mono = time.monotonic()

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        df = pd.read_csv(BytesIO(raw))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {type(e).__name__}: {e}")

    if df.shape[1] == 0:
        raise HTTPException(status_code=400, detail="CSV has no columns")

    row_count = int(df.shape[0])
    column_count = int(df.shape[1])

    # STEP 1: create dataset
    dataset = Dataset(
        name=dataset_name,
        description=description,
        row_count=row_count,
        column_count=column_count,
    )
    db.add(dataset)
    db.flush()  # dataset.id available

    # PREVIEW: persist first N rows now (JSON-safe: no NaN/Infinity)
    preview_df = df.head(PREVIEW_ROWS).copy()

    # Convert pandas/NumPy scalars -> plain python types and replace NaN/Inf -> None
    preview_rows: list[dict[str, Any]] = []
    for rec in preview_df.to_dict(orient="records"):
        clean: dict[str, Any] = {}
        for k, v in rec.items():
            if v is None:
                clean[k] = None
                continue

            # pandas missing values
            if pd.isna(v):
                clean[k] = None
                continue

            # convert numpy scalars to python scalars
            if hasattr(v, "item"):
                try:
                    v = v.item()
                except Exception:
                    pass

            # disallow NaN/Inf (can appear after .item())
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                clean[k] = None
            else:
                clean[k] = v
        preview_rows.append(clean)

    db.add(DatasetPreview(dataset_id=dataset.id, rows=preview_rows))

    # STEP 2: create run early
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

    try:
        # move to profiling
        run.status = "profiling"
        run.message = "Profiling started"
        db.add(run)
        db.commit()
        db.refresh(run)

        # STEP 3: create columns + stats
        for col in df.columns:
            s = df[col]

            null_count = int(s.isna().sum())
            distinct_count = int(s.dropna().astype(str).nunique())

            col_obj = DatasetColumn(
                dataset_id=dataset.id,
                name=str(col),
                dtype=str(s.dtype),
                null_count=null_count,
                distinct_count=distinct_count,
            )
            db.add(col_obj)
            db.flush()  # col_obj.id available

            # Stats only for numeric columns
            if is_numeric_dtype(s):
                stats = _compute_numeric_stats(s)
                if stats is not None:
                    db.add(
                        ColumnStatistics(
                            column_id=col_obj.id,
                            mean=stats["mean"],
                            std=stats["std"],
                            min=stats["min"],
                            max=stats["max"],
                            outlier_count=stats["outlier_count"],
                            outlier_ratio=stats["outlier_ratio"],
                            skewness=stats["skewness"],
                            kurtosis=stats.get("kurtosis"),
                        )
                    )

        # finalize run
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

        # best-effort failure record
        try:
            run.status = "failed"
            run.message = "Ingestion failed"
            run.error_message = f"{type(e).__name__}: {e}"
            run.completed_at = finished_wall
            run.duration_ms = duration_ms
            db.add(run)
            db.commit()
        except Exception:
            db.rollback()

        raise HTTPException(status_code=500, detail=f"Ingestion failed: {type(e).__name__}: {e}")
