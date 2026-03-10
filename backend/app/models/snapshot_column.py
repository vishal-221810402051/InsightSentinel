from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class SnapshotColumn(Base):
    __tablename__ = "snapshot_columns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    snapshot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(255), nullable=False)
    dtype = Column(String(100), nullable=False)
    null_count = Column(Integer, nullable=False)
    distinct_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    snapshot = relationship("DatasetSnapshot")
