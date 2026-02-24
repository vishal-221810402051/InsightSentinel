from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)

    # e.g. THRESHOLD, ANOMALY, DRIFT (we'll expand later)
    rule_type = Column(String(64), nullable=False)

    # JSON config for rule parameters (threshold, column, operator, etc.)
    config = Column(JSONB, nullable=False, default=dict)

    is_enabled = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    dataset = relationship("Dataset")
