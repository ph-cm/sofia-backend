from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.services.analytics_service import get_analytics_summary

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary")
def analytics_summary(
    tenant_id: int,
    from_: str,
    to: str,
    db: Session = Depends(get_db)
):

    data = get_analytics_summary(db, tenant_id, from_, to)

    return {
        "tenant_id": tenant_id,
        "from": from_,
        "to": to,
        **data
    }