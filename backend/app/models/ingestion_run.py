from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Lifecycle: created -> profiling -> completed | failed
    status = Column(String(50), nullable=False, default="created")

    message = Column(String(500), nullable=False, default="Ingestion started")

    # Store failure info (keep minimal for now)
    error_message = Column(String(1000), nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    duration_ms = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # FIX: no trailing comma here
    dataset = relationship("Dataset", back_populates="ingestion_runs")