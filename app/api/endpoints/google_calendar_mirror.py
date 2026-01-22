from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db  # ajuste se o path for diferente
from app.api.services.google_calendar_mirror import list_events_range

router = APIRouter(prefix="/google", tags=["google-calendar-mirror"])

@router.get("/events/range")
def google_events_range(
    user_id: int = Query(...),
    calendar_id: str = Query("primary"),
    time_min: Optional[datetime] = Query(None),
    time_max: Optional[datetime] = Query(None),
    telefone: Optional[str] = Query(None),
    maxResults: int = Query(250, ge=1, le=2500),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
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
        # mantém o padrão do FastAPI pro front entender
        raise HTTPException(status_code=400, detail=str(e))
