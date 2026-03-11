from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.column_statistics import ColumnStatistics
from app.models.dataset_column import DatasetColumn
from app.models.dataset_snapshot import DatasetSnapshot
from app.models.snapshot_column import SnapshotColumn
from app.models.snapshot_statistics import SnapshotStatistics


def get_latest_snapshot(db: Session, dataset_id) -> DatasetSnapshot | None:
    return (
        db.query(DatasetSnapshot)
        .filter(DatasetSnapshot.dataset_id == dataset_id)
        .order_by(DatasetSnapshot.created_at.desc())
        .first()
    )


def get_latest_snapshot_profile_context(
    db: Session, dataset_id
) -> tuple[DatasetSnapshot | None, dict[str, Any], dict[str, Any]]:
    """
    Returns profiling context for a monitored dataset:
      - latest snapshot if available
      - columns_by_name
      - stats_by_column_id (keyed by column id as string)

    Falls back to legacy dataset-level profiling tables for older datasets.
    """
    snapshot = get_latest_snapshot(db, dataset_id)

    if snapshot is not None:
        columns = (
            db.query(SnapshotColumn)
            .filter(SnapshotColumn.snapshot_id == snapshot.id)
            .all()
        )
        column_ids = [c.id for c in columns]
        if column_ids:
            stats = (
                db.query(SnapshotStatistics)
                .filter(SnapshotStatistics.snapshot_column_id.in_(column_ids))
                .all()
            )
        else:
            stats = []

        columns_by_name = {c.name: c for c in columns}
        stats_by_col_id = {str(s.snapshot_column_id): s for s in stats}
        return snapshot, columns_by_name, stats_by_col_id

    columns = (
        db.query(DatasetColumn)
        .filter(DatasetColumn.dataset_id == dataset_id)
        .all()
    )
    stats = (
        db.query(ColumnStatistics)
        .join(DatasetColumn, DatasetColumn.id == ColumnStatistics.column_id)
        .filter(DatasetColumn.dataset_id == dataset_id)
        .all()
    )
    columns_by_name = {c.name: c for c in columns}
    stats_by_col_id = {str(s.column_id): s for s in stats}
    return None, columns_by_name, stats_by_col_id
