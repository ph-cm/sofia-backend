from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.services.google_calendar_service import GoogleCalendarService
from app.api.services.google_token_service import GoogleTokenService
from app.db.session import get_db

router = APIRouter(prefix="/google/events", tags=["Google Calendar Events"])

google_calendar = GoogleCalendarService()


@router.put("/update")
def update_google_event(
    user_id: int,
    event_id: str,
    titulo: str,
    descricao: str,
    inicio: str,
    fim: str,
    timezone: str = "America/Sao_Paulo",
    id_agenda: str = "primary",
    db: Session = Depends(get_db)
):
    try:
        # 1) Pegamos tokens do banco
        token = GoogleTokenService.get_by_user(db, user_id)
        if not token:
            raise HTTPException(404, "Token Google não encontrado.")

        # 2) Update do evento
        updated_event = google_calendar.update_event(
            token=token,
            calendar_id=id_agenda,
            event_id=event_id,
            title=titulo,
            description=descricao,
            start=inicio,
            end=fim,
            timezone=timezone
        )

        return updated_event

    except Exception as e:
        raise HTTPException(400, str(e))
