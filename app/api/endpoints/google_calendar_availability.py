from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.api.services.google_token_service import GoogleTokenService
from app.api.services.google_calendar_service import GoogleCalendarService

router = APIRouter(prefix="/google", tags=["Google Calendar Availability"])

google_calendar_service = GoogleCalendarService()


class AvailabilityPayload(BaseModel):
    user_id: int
    start_date: str
    end_date: str
    timezone: str = "America/Sao_Paulo"


@router.post("/availability")
def get_google_availability(payload: AvailabilityPayload, db: Session = Depends(get_db)):

    try:
        token = GoogleTokenService.get_token_by_user(db, payload.user_id)
        if not token:
            raise HTTPException(status_code=404, detail="Token do usuário não encontrado.")

        free_slots = google_calendar_service.get_availability(
            token=token,
            start_date=payload.start_date,
            end_date=payload.end_date,
            timezone=payload.timezone
        )

        return {
            "user_id": payload.user_id,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
            "timezone": payload.timezone,
            "available_slots": free_slots
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
