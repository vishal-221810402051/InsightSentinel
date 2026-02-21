from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ColumnStatisticsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mean: Optional[float] = None
    std: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    outlier_count: Optional[int] = None
    outlier_ratio: Optional[float] = None
    created_at: Optional[datetime] = None


class DatasetColumnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    dtype: str
    null_count: int
    distinct_count: int
    created_at: datetime

    statistics: Optional[ColumnStatisticsOut] = None


class DatasetListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str = ""
    row_count: int
    column_count: int
    created_at: datetime


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str = ""
    row_count: int
    column_count: int
    created_at: datetime

    columns: list[DatasetColumnOut] = []