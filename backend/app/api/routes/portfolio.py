from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.portfolio_engine import compute_portfolio_overview

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/overview")
def portfolio_overview(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return compute_portfolio_overview(db, owner_id=current_user.id, limit=limit)
