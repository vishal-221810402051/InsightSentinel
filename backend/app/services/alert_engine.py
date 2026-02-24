from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
import math
from typing import Any, Callable, Dict, Optional

from sqlalchemy.orm import Session

from app.models.alert_event import AlertEvent
from app.models.alert_rule import AlertRule
from app.models.column_statistics import ColumnStatistics
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_insight import DatasetInsight
from app.models.dataset_preview import DatasetPreview

_USE_STRATEGY = True
_COOLDOWN_MINUTES = 10
_SUPPORTED_OPS = {">", ">=", "<", "<=", "==", "!="}
_SUPPORTED_SCOPES = {"latest", "any", "mean"}
logger = logging.getLogger(__name__)


@dataclass
class RuleContext:
    row_count: int
    preview_rows: list[dict]
    columns_by_name: dict[str, Any]
    stats_by_col_id: dict[str, Any]


@dataclass
class AlertEvalSummary:
    created_events: int = 0
    evaluated_rules: int = 0
    skipped_rules: int = 0
    no_signal_rules: int = 0
    unsupported_rules: int = 0


RuleHandler = Callable[[Session, Any, RuleContext], int]

RULE_HANDLERS: Dict[str, RuleHandler] = {}


def register(rule_type: str):
    def _wrap(fn: RuleHandler):
        RULE_HANDLERS[rule_type] = fn
        return fn

    return _wrap


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_preview_rows(db: Session, dataset_id) -> list[dict]:
    p = db.query(DatasetPreview).filter(DatasetPreview.dataset_id == dataset_id).first()
    return p.rows if p and p.rows else []


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
        if not math.isfinite(f):
            return None
        return f
    except Exception:
        return None


def _compare(value: float, op: str, threshold: float) -> bool:
    if op == ">":
        return value > threshold
    if op == ">=":
        return value >= threshold
    if op == "<":
        return value < threshold
    if op == "<=":
        return value <= threshold
    if op == "==":
        return value == threshold
    if op == "!=":
        return value != threshold
    return False


def _compute_value_from_preview(preview_rows: list[dict], column: str, scope: str) -> Optional[float]:
    if not preview_rows:
        return None

    scope = (scope or "latest").lower()

    vals = []
    for r in preview_rows:
        if isinstance(r, dict) and column in r:
            vals.append(_to_float(r.get(column)))
    vals = [x for x in vals if x is not None]
    if not vals:
        return None

    if scope == "latest":
        return vals[-1]

    if scope == "mean":
        return sum(vals) / len(vals)

    return None


def _collect_values_from_preview(preview_rows: list[dict], column: str) -> list[float]:
    vals: list[float] = []
    for r in preview_rows:
        if isinstance(r, dict) and column in r:
            fv = _to_float(r.get(column))
            if fv is not None:
                vals.append(fv)
    return vals


def _cooldown_exists(db: Session, dataset_id, rule_id) -> bool:
    cutoff = _now() - timedelta(minutes=_COOLDOWN_MINUTES)
    q = (
        db.query(AlertEvent)
        .filter(AlertEvent.dataset_id == dataset_id)
        .filter(AlertEvent.rule_id == rule_id)
        .filter(AlertEvent.created_at >= cutoff)
    )
    return db.query(q.exists()).scalar() is True


@register("THRESHOLD")
def _handle_threshold_rule(db: Session, rule: Any, ctx: RuleContext) -> int:
    cfg = rule.config if isinstance(rule.config, dict) else {}
    col_name = cfg.get("column")
    op = cfg.get("op")
    threshold = cfg.get("threshold")
    scope_raw = cfg.get("scope")
    scope = str(scope_raw).lower() if scope_raw is not None else "latest"

    if col_name is None or threshold is None:
        return 0

    col_name = str(col_name).strip()
    op = str(op).strip()

    if not col_name or op not in _SUPPORTED_OPS or scope not in _SUPPORTED_SCOPES:
        return 0

    t = _to_float(threshold)
    if t is None:
        return 0

    if _cooldown_exists(db, rule.dataset_id, rule.id):
        return 0

    triggered = False
    evidence: dict[str, Any] = {"scope": scope, "column": col_name, "op": op, "threshold": float(t)}

    try:
        if scope == "latest":
            value = _compute_value_from_preview(ctx.preview_rows, col_name, "latest")
            if value is None:
                return 0
            triggered = _compare(value, op, t)
            evidence["value"] = float(value)

        elif scope == "any":
            vals = _collect_values_from_preview(ctx.preview_rows, col_name)
            if not vals:
                return 0
            bad = [v for v in vals if _compare(v, op, t)]
            triggered = len(bad) > 0
            evidence["violations"] = bad[:10]
            evidence["violation_count"] = len(bad)
            evidence["checked_count"] = len(vals)

        elif scope == "mean":
            mean_v = None
            col = ctx.columns_by_name.get(col_name)
            if col is not None:
                stats = ctx.stats_by_col_id.get(str(col.id))
                if stats is not None:
                    mean_v = stats.mean
            if mean_v is None:
                mean_v = _compute_value_from_preview(ctx.preview_rows, col_name, "mean")
            if mean_v is None:
                return 0

            triggered = _compare(float(mean_v), op, t)
            evidence["mean"] = float(mean_v)
        else:
            return 0
    except Exception:
        return 0

    if not triggered:
        return 0

    db.add(
        AlertEvent(
            dataset_id=rule.dataset_id,
            rule_id=rule.id,
            severity="warning",
            title=f"Rule triggered: {rule.name}",
            message=f"THRESHOLD rule triggered on '{col_name}' ({op} {t}).",
            payload=evidence,
        )
    )
    return 1


@register("NULL_RATIO")
def _handle_null_ratio_rule(db: Session, rule: Any, ctx: RuleContext) -> int:
    cfg = rule.config if isinstance(rule.config, dict) else {}
    col_name = cfg.get("column")
    op = cfg.get("op")
    threshold = cfg.get("threshold")

    if col_name is None or threshold is None:
        return 0

    col_name = str(col_name).strip()
    op = str(op).strip()

    if not col_name or op not in _SUPPORTED_OPS:
        return 0

    t = _to_float(threshold)
    if t is None:
        return 0

    col = ctx.columns_by_name.get(col_name)
    if col is None or ctx.row_count <= 0:
        return 0

    null_ratio = (col.null_count or 0) / max(ctx.row_count, 1)

    if not _compare(null_ratio, op, t):
        return 0

    if _cooldown_exists(db, rule.dataset_id, rule.id):
        return 0

    db.add(
        AlertEvent(
            dataset_id=rule.dataset_id,
            rule_id=rule.id,
            severity="warning",
            title=f"Rule triggered: {rule.name}",
            message=f"NULL_RATIO rule triggered on '{col_name}' ({op} {t}).",
            payload={
                "column": col_name,
                "null_ratio": float(null_ratio),
                "op": op,
                "threshold": float(t),
            },
        )
    )
    return 1


@register("OUTLIER_RATIO")
def _handle_outlier_ratio_rule(db: Session, rule: Any, ctx: RuleContext) -> int:
    cfg = rule.config if isinstance(rule.config, dict) else {}
    col_name = cfg.get("column")
    op = cfg.get("op")
    threshold = cfg.get("threshold")

    if col_name is None or threshold is None:
        return 0

    col_name = str(col_name).strip()
    op = str(op).strip()

    if not col_name or op not in _SUPPORTED_OPS:
        return 0

    t = _to_float(threshold)
    if t is None:
        return 0

    col = ctx.columns_by_name.get(col_name)
    if col is None:
        return 0

    stats = ctx.stats_by_col_id.get(str(col.id))
    if stats is None or stats.outlier_ratio is None:
        return 0

    outlier_ratio = float(stats.outlier_ratio)

    if not _compare(outlier_ratio, op, t):
        return 0

    if _cooldown_exists(db, rule.dataset_id, rule.id):
        return 0

    db.add(
        AlertEvent(
            dataset_id=rule.dataset_id,
            rule_id=rule.id,
            severity="warning",
            title=f"Rule triggered: {rule.name}",
            message=f"OUTLIER_RATIO rule triggered on '{col_name}' ({op} {t}).",
            payload={
                "column": col_name,
                "outlier_ratio": outlier_ratio,
                "op": op,
                "threshold": float(t),
            },
        )
    )
    return 1


@register("INSIGHT_PRESENT")
def _handle_insight_present_rule(db: Session, rule: Any, ctx: RuleContext) -> int:
    cfg = rule.config if isinstance(rule.config, dict) else {}
    code = cfg.get("code")

    if not code:
        return 0

    code = str(code).strip()

    exists = (
        db.query(DatasetInsight)
        .filter(DatasetInsight.dataset_id == rule.dataset_id)
        .filter(DatasetInsight.code == code)
        .first()
    )

    if exists is None:
        return 0

    if _cooldown_exists(db, rule.dataset_id, rule.id):
        return 0

    db.add(
        AlertEvent(
            dataset_id=rule.dataset_id,
            rule_id=rule.id,
            severity="warning",
            title=f"Rule triggered: {rule.name}",
            message=f"INSIGHT_PRESENT rule triggered (code='{code}').",
            payload={"code": code},
        )
    )
    return 1


def evaluate_alerts_for_dataset(db: Session, dataset_id) -> AlertEvalSummary:
    """
    Evaluate enabled rules for dataset using rule handlers.
    Returns an evaluation summary including created/skipped/unsupported counts.
    """
    summary = AlertEvalSummary()
    rules = (
        db.query(AlertRule)
        .filter(AlertRule.dataset_id == dataset_id)
        .filter(AlertRule.is_enabled == True)  # noqa: E712
        .order_by(AlertRule.created_at.asc())
        .all()
    )
    if not rules:
        return summary

    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        return summary

    preview = db.query(DatasetPreview).filter(DatasetPreview.dataset_id == dataset_id).first()
    preview_rows = preview.rows if preview and preview.rows else []
    columns = db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).all()
    stats = (
        db.query(ColumnStatistics)
        .join(DatasetColumn, DatasetColumn.id == ColumnStatistics.column_id)
        .filter(DatasetColumn.dataset_id == dataset_id)
        .all()
    )
    ctx = RuleContext(
        row_count=int(dataset.row_count or 0),
        preview_rows=preview_rows,
        columns_by_name={c.name: c for c in columns},
        stats_by_col_id={str(s.column_id): s for s in stats},
    )

    for rule in rules:
        handler = RULE_HANDLERS.get(rule.rule_type)
        if handler is None:
            summary.unsupported_rules += 1
            continue

        if _cooldown_exists(db, rule.dataset_id, rule.id):
            summary.skipped_rules += 1
            continue

        summary.evaluated_rules += 1
        try:
            created = int(handler(db, rule, ctx) or 0)
            summary.created_events += created
            if created == 0:
                summary.no_signal_rules += 1
        except Exception:
            summary.no_signal_rules += 1
            logger.exception(
                "Alert handler failed for rule_id=%s, rule_type=%s",
                rule.id,
                rule.rule_type,
            )
            continue

    if summary.created_events > 0:
        db.commit()
    return summary


def _evaluate_dataset_rules_legacy(db: Session, dataset_id) -> int:
    """
    Legacy path retained temporarily for rollback safety during 5C-A refactor.
    """
    rules = (
        db.query(AlertRule)
        .filter(AlertRule.dataset_id == dataset_id)
        .filter(AlertRule.is_enabled == True)  # noqa: E712
        .order_by(AlertRule.created_at.asc())
        .all()
    )
    if not rules:
        return 0

    preview_rows = _get_preview_rows(db, dataset_id)

    created = 0
    for rule in rules:
        if rule.rule_type != "THRESHOLD":
            continue

        cfg = rule.config if isinstance(rule.config, dict) else {}
        col_name = cfg.get("column")
        op = cfg.get("op")
        threshold = cfg.get("threshold")
        scope_raw = cfg.get("scope")
        scope = "latest" if scope_raw in (None, "") else str(scope_raw).lower()

        if col_name is None or threshold is None:
            continue

        col_name = str(col_name).strip()
        op = str(op).strip()

        if not col_name or op not in _SUPPORTED_OPS or scope not in _SUPPORTED_SCOPES:
            continue

        try:
            t = float(threshold)
            if not math.isfinite(t):
                continue
        except Exception:
            continue

        if _cooldown_exists(db, dataset_id, rule.id):
            continue

        triggered = False
        evidence: dict[str, Any] = {"scope": scope, "column": col_name, "op": op, "threshold": t}

        try:
            if scope in ("latest", "any"):
                vals = _collect_values_from_preview(preview_rows, col_name)
                if not vals:
                    continue

                if scope == "latest":
                    v = vals[-1]
                    triggered = _compare(v, op, t)
                    evidence["value"] = v
                else:
                    bad = [v for v in vals if _compare(v, op, t)]
                    triggered = len(bad) > 0
                    evidence["violations"] = bad[:10]
                    evidence["violation_count"] = len(bad)
                    evidence["checked_count"] = len(vals)

            elif scope == "mean":
                mean_v = None
                col = (
                    db.query(DatasetColumn)
                    .filter(DatasetColumn.dataset_id == dataset_id)
                    .filter(DatasetColumn.name == col_name)
                    .first()
                )
                if col and col.statistics:
                    mean_v = col.statistics.mean
                if mean_v is None:
                    mean_v = _compute_value_from_preview(preview_rows, col_name, "mean")

                if mean_v is None:
                    continue

                triggered = _compare(float(mean_v), op, t)
                evidence["mean"] = float(mean_v)
            else:
                continue
        except Exception:
            continue

        if triggered:
            db.add(
                AlertEvent(
                    dataset_id=dataset_id,
                    rule_id=rule.id,
                    severity="warning",
                    title=f"Rule triggered: {rule.name}",
                    message=f"THRESHOLD rule triggered on '{col_name}' ({op} {t}).",
                    payload=evidence,
                )
            )
            created += 1

    if created > 0:
        db.commit()
    return created


def evaluate_dataset_rules(db: Session, dataset_id) -> AlertEvalSummary:
    """
    Evaluate enabled rules for dataset using preview + (optional) ColumnStatistics.
    Returns an evaluation summary.
    """
    if _USE_STRATEGY:
        return evaluate_alerts_for_dataset(db, dataset_id)
    created = _evaluate_dataset_rules_legacy(db, dataset_id)
    return AlertEvalSummary(created_events=int(created))
