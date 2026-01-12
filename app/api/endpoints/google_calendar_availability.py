from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.services.google_token_service import GoogleTokenService
from app.api.services.google_calendar_service import list_calendars
from app.api.services.google_calendar_service import GoogleCalendarService

router = APIRouter(prefix="/google", tags=["Google Calendar Availability"])

google_calendar_service = GoogleCalendarService()


@router.get("/availability")
def get_google_availability(
    user_id: int = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    timezone: str = Query("America/Sao_Paulo"),
    db: Session = Depends(get_db)
):

    try:
        # 1️⃣ Buscar token do usuário (do seu google_token_service)
        token = GoogleTokenService.get_token_by_user(db, user_id)
        if not token:
            raise HTTPException(status_code=404, detail="Token do usuário não encontrado.")

        # 2️⃣ Chamamos o serviço que consulta o Google Calendar
        free_slots = google_calendar_service.get_availability(
            token=token,
            start_date=start_date,
            end_date=end_date,
            timezone=timezone
        )

        return {
            "user_id": user_id,
            "available_slots": free_slots
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
