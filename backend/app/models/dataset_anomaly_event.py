from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class DatasetAnomalyEvent(Base):
    __tablename__ = "dataset_anomaly_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    metric = Column(String(50), nullable=False)  # e.g. "risk_score"
    value = Column(Float, nullable=False)
    rolling_mean = Column(Float, nullable=True)
    rolling_std = Column(Float, nullable=True)
    z_score = Column(Float, nullable=True)
    window = Column(Integer, nullable=False)
    threshold = Column(Float, nullable=False)
    direction = Column(String(10), nullable=True)  # "spike" / "drop"
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


Index(
    "ix_dataset_anomaly_events_dataset_created",
    DatasetAnomalyEvent.dataset_id,
    DatasetAnomalyEvent.created_at.desc(),
)
Index(
    "ix_dataset_anomaly_events_dataset_metric_created",
    DatasetAnomalyEvent.dataset_id,
    DatasetAnomalyEvent.metric,
    DatasetAnomalyEvent.created_at.desc(),
)

