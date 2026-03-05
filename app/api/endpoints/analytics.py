# app/api/endpoints/analytics.py
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/summary")
def analytics_summary(
    tenant_id: int,
    from_: date = Query(..., alias="from"),
    to: date = Query(...),
    user_id: int | None = None,
    db: Session = Depends(get_db),
):
    return AnalyticsService.summary(
        db=db,
        tenant_id=tenant_id,
        date_from=from_,
        date_to=to,
        user_id=user_id
    )