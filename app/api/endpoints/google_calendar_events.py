from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.services.google_token_service import GoogleTokenService
from app.api.services.google_calendar_service import GoogleCalendarService

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
