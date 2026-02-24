from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class DatasetRiskHistory(Base):
    __tablename__ = "dataset_risk_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    risk_score = Column(Integer, nullable=False)
    risk_level = Column(String(20), nullable=False)  # low | moderate | high | critical
    breakdown = Column(JSONB, nullable=False)  # {"insight_score":..., ...}
    smoothed_score = Column(Integer, nullable=True)
    alpha = Column(Float, nullable=True)
    delta_score = Column(Float, nullable=True)
    accel_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
