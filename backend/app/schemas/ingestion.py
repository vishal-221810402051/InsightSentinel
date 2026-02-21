from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel


class IngestionRunOut(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    status: str
    message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class IngestCsvResponse(BaseModel):
    dataset_id: uuid.UUID
    ingestion_run: IngestionRunOut