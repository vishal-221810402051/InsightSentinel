from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class DatasetInsightOut(BaseModel):
    dataset_id: uuid.UUID
    column_id: uuid.UUID | None = None
    severity: str
    code: str
    title: str
    message: str
    created_at: datetime | None = None


class DatasetInsightsResponseOut(BaseModel):
    dataset_id: uuid.UUID
    refreshed: bool
    count: int
    insights: list[DatasetInsightOut]
