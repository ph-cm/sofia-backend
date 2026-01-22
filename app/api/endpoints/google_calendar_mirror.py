from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db  # ajuste se o path for diferente
from app.schemas.google_events import GoogleEventOut
from app.api.services.google_calendar_mirror import list_events_range

router = APIRouter(prefix="/google", tags=["google-calendar-mirror"])

@router.get("/events/range", response_model=List[GoogleEventOut])
def google_events_range(
    user_id: int = Query(..., description="ID do usuário (tenant/profissional)"),
    calendar_id: str = Query("primary", description="ID da agenda no Google"),
    time_min: Optional[datetime] = Query(None, description="ISO datetime ex: 2026-01-22T00:00:00-03:00"),
    time_max: Optional[datetime] = Query(None, description="ISO datetime"),
    telefone: Optional[str] = Query(None, description="Filtra eventos que contenham o telefone (opcional)"),
    maxResults: int = Query(250, ge=1, le=2500),
    db: Session = Depends(get_db),
):
    try:
        return list_events_range(
            db=db,
            user_id=user_id,
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
            telefone=telefone,
            max_results=maxResults,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
