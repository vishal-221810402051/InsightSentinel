from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Dataset, IngestionRun, DatasetColumn

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/csv")
async def ingest_csv(
    dataset_name: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
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

        # 1) Create dataset
        dataset = Dataset(
            name=dataset_name,
            description=description,
            row_count=row_count,
            column_count=column_count,
        )
        db.add(dataset)
        db.flush()  # ensures dataset.id exists in DB (FK-safe)

        # 2) Create ingestion run
        run = IngestionRun(
            dataset_id=dataset.id,
            status="created",
            message="Ingestion started",
        )
        db.add(run)

        # 3) Create dataset columns
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

        db.commit()
        db.refresh(dataset)
        db.refresh(run)

        return {
            "dataset_id": str(dataset.id),
            "run_id": str(run.id),
            "name": dataset.name,
            "description": dataset.description,
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
            "status": run.status,
            "message": "Dataset + columns + ingestion run saved (Phase 2 full).",
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {type(e).__name__}: {e}")