from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class DatasetColumnCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    dtype: str = Field(..., min_length=1, max_length=100)
    null_count: int | None = None
    distinct_count: int | None = None


class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    row_count: int | None = None
    column_count: int | None = None
    columns: list[DatasetColumnCreate] = Field(default_factory=list)


class DatasetColumnOut(BaseModel):
    id: uuid.UUID
    name: str
    dtype: str
    null_count: int | None
    distinct_count: int | None

    model_config = {"from_attributes": True}


class DatasetOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    row_count: int | None
    column_count: int | None
    created_at: datetime
    columns: list[DatasetColumnOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class DatasetListOut(BaseModel):
    id: uuid.UUID
    name: str
    row_count: int | None
    column_count: int | None
    created_at: datetime

    model_config = {"from_attributes": True}