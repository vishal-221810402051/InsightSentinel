from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel


class DatasetPreviewOut(BaseModel):
    dataset_id: uuid.UUID
    columns: list[str]
    rows: list[dict[str, Any]]
    returned_rows: int
    stored_rows: int
