from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.services.google_token_service import GoogleTokenService
from app.api.services.google_calendar_service import GoogleCalendarService, google_calendar_service
from app.schemas.google_events import GoogleEventCreateIn, GoogleEventCreateOut
from app.api.services.google_calendar_events_service import GoogleCalendarEventsService

router = APIRouter(prefix="/google/events", tags=["google-calendar"])

calendar_service = GoogleCalendarService()


@router.get("/list")
def list_google_events(
    user_id: int,
    id_agenda: str = "primary",
    telefone: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Lista eventos do Google Calendar do usuário.
    Suporta filtro por telefone dentro de summary/description.
    """

    # 1. Buscar token do usuário
    token = GoogleTokenService.get_by_user(db, user_id)
    if not token:
        raise HTTPException(status_code=404, detail="Usuário não conectado ao Google")

    try:
        # 2. Listar todos os eventos usando o service GoogleCalendarService
        events = calendar_service.list_events(token, id_agenda)

        # 3. Se telefone foi enviado, realizar filtragem
        if telefone:
            telefone = telefone.strip()

            filtered = [
                evt for evt in events
                if telefone in (evt.get("summary", "") + evt.get("description", ""))
            ]

            return {
                "total": len(filtered),
                "filtered": True,
                "events": filtered,
            }

        # 4. Retornar todos
        return {
            "total": len(events),
            "filtered": False,
            "events": events,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{event_id}")
def delete_google_event(
    event_id: str,
    calendar_id: str,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Remove um evento do Google Calendar.
    """
    try:
        # 1) pegar token do user
        token = GoogleTokenService.get_by_user(db, user_id)
        if not token:
            raise HTTPException(404, "Token Google não encontrado para o usuário.")

        # 2) chamar Google Calendar API via service
        google_calendar_service.delete_event(
            token=token,
            calendar_id=calendar_id,
            event_id=event_id
        )

        return {"status": "deleted", "event_id": event_id}

    except Exception as e:
        raise HTTPException(400, str(e))
    
@router.post("/create", response_model=GoogleEventCreateOut)
def create_google_event(payload: GoogleEventCreateIn, db: Session = Depends(get_db)):
    access_token = GoogleTokenService.get_valid_access_token(db, payload.user_id)

    event = GoogleCalendarEventsService.create_event(
        access_token=access_token,
        calendar_id=payload.calendar_id,
        start_datetime=payload.start_datetime,
        end_datetime=payload.end_datetime,
        summary=payload.summary,
        description=payload.description or "",
        timezone=payload.timezone or "America/Sao_Paulo",
    )

    return {
        "status": "ok",
        "event": {
            "id": event.get("id"),
            "htmlLink": event.get("htmlLink"),
            "calendar_id": payload.calendar_id,
            "summary": event.get("summary"),
            "description": event.get("description"),
            "start": (event.get("start") or {}).get("dateTime"),
            "end": (event.get("end") or {}).get("dateTime"),
        },
    }