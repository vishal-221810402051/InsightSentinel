from __future__ import annotations

import hashlib

from sqlalchemy import text
from sqlalchemy.orm import Session


def _lock_id(key: str) -> int:
    """
    Convert string key to signed 64-bit integer for pg advisory lock.
    """
    h = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(h[:8], byteorder="big", signed=True)


def try_advisory_lock(db: Session, key: str) -> bool:
    lock_id = _lock_id(key)
    result = db.execute(
        text("SELECT pg_try_advisory_lock(:id)"),
        {"id": lock_id},
    ).scalar()
    return bool(result)


def advisory_unlock(db: Session, key: str) -> None:
    lock_id = _lock_id(key)
    db.execute(
        text("SELECT pg_advisory_unlock(:id)"),
        {"id": lock_id},
    )
