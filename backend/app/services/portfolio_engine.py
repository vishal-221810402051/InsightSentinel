from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.dataset_risk_history import DatasetRiskHistory


def compute_portfolio_overview(db: Session, owner_id, limit: int = 10) -> Dict[str, Any]:
    """
    Portfolio-level intelligence based on the latest risk snapshot per dataset:
      - top_risk: highest smoothed_score (fallback to risk_score)
      - top_movers: largest absolute delta_score
      - fastest_accelerating: largest absolute accel_score
    Efficient: uses GROUP BY MAX(created_at) subquery.
    """
    limit = max(1, min(int(limit or 10), 100))

    # Latest row per dataset_id.
    subq = (
        db.query(
            DatasetRiskHistory.dataset_id.label("dataset_id"),
            func.max(DatasetRiskHistory.created_at).label("max_ts"),
        )
        .join(Dataset, Dataset.id == DatasetRiskHistory.dataset_id)
        .filter(Dataset.owner_id == owner_id)
        .group_by(DatasetRiskHistory.dataset_id)
        .subquery()
    )

    latest_rows: List[DatasetRiskHistory] = (
        db.query(DatasetRiskHistory)
        .join(
            subq,
            (DatasetRiskHistory.dataset_id == subq.c.dataset_id)
            & (DatasetRiskHistory.created_at == subq.c.max_ts),
        )
        .all()
    )

    rows: List[Dict[str, Any]] = []
    for r in latest_rows:
        smoothed = getattr(r, "smoothed_score", None)
        delta = getattr(r, "delta_score", None)
        accel = getattr(r, "accel_score", None)

        # Fallback-safe.
        risk_base = int(r.risk_score or 0)
        smoothed_v = int(smoothed if smoothed is not None else risk_base)
        delta_v = float(delta or 0.0)
        accel_v = float(accel or 0.0)

        rows.append(
            {
                "dataset_id": str(r.dataset_id),
                "risk_score": risk_base,
                "risk_level": r.risk_level,
                "smoothed_score": smoothed_v,
                "delta_score": delta_v,
                "accel_score": accel_v,
                "created_at": r.created_at,
            }
        )

    top_risk = sorted(rows, key=lambda x: x["smoothed_score"], reverse=True)[:limit]
    top_movers = sorted(rows, key=lambda x: abs(x["delta_score"]), reverse=True)[:limit]
    fastest_accel = sorted(rows, key=lambda x: abs(x["accel_score"]), reverse=True)[:limit]

    return {
        "count": len(rows),
        "top_risk": top_risk,
        "top_movers": top_movers,
        "fastest_accelerating": fastest_accel,
    }
