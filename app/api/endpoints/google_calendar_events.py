from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from fastapi import status
from app.db.session import get_db
from app.api.services.google_token_service import GoogleTokenService
from app.api.services.google_calendar_service import google_calendar_service
from app.api.services.google_calendar_events_service import GoogleCalendarEventsService
from app.schemas.google_events import GoogleEventCreateIn, GoogleEventCreateOut, GoogleEventUpdateIn, GoogleEventUpdateOut
from app.api.services.google_calendar_events_crud import google_calendar_events_crud
from datetime import datetime

router = APIRouter(prefix="/google/events", tags=["google-calendar"])


@router.get("/list")
def list_google_events(
    user_id: int = Query(..., description="ID do usuário (tenant/profissional)"),
    calendar_id: str = Query("primary", description="ID da agenda no Google (default: primary)"),
    telefone: str | None = Query(None, description="Filtra eventos que contenham o telefone em summary/description"),
    db: Session = Depends(get_db),
):
    token = GoogleTokenService.get_by_user(db, user_id)
    if not token:
        raise HTTPException(status_code=404, detail="Usuário não conectado ao Google")

    try:
        events = google_calendar_service.list_events(token, calendar_id)

        if telefone:
            tel = telefone.strip()
            filtered = [
                evt for evt in events
                if tel in ((evt.get("summary") or "") + (evt.get("description") or ""))
            ]
            return {"total": len(filtered), "filtered": True, "events": filtered}

        return {"total": len(events), "filtered": False, "events": events}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.delete("/{event_id}", status_code=status.HTTP_200_OK)
def delete_google_event(
    event_id: str,
    user_id: int = Query(..., description="ID do usuário (tenant/profissional)"),
    calendar_id: str = Query("primary", description="ID da agenda no Google (default: primary)"),
    db: Session = Depends(get_db),
):
    token = GoogleTokenService.get_by_user(db, user_id)
    if not token:
        raise HTTPException(status_code=404, detail="Usuário não conectado ao Google")

    try:
        google_calendar_service.delete_event(db, token, calendar_id, event_id)
        return {"status": "deleted", "event_id": event_id, "calendar_id": calendar_id}
    except Exception as e:
        # Se quiser melhorar depois: parsear e.status_code do Google
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/create", response_model=GoogleEventCreateOut)
def create_google_event(payload: GoogleEventCreateIn, db: Session = Depends(get_db)):
    """
    Cria um evento no Google Calendar usando token do usuário salvo no banco.
    Retorna sempre no formato do GoogleEventCreateOut.
    """
    try:
        access_token = GoogleTokenService.get_valid_access_token(db, payload.user_id)

        event = GoogleCalendarEventsService.create_event(
            access_token=access_token,
            calendar_id=payload.calendar_id or "primary",
            start_datetime=payload.start_datetime,
            end_datetime=payload.end_datetime,
            summary=payload.summary,
            description=payload.description or "",
            timezone=payload.timezone or "America/Sao_Paulo",
        )

        return GoogleEventCreateOut(
            status="ok",
            motivo=None,
            event={
                "id": event.get("id"),
                "htmlLink": event.get("htmlLink"),
                "calendar_id": payload.calendar_id or "primary",
                "summary": event.get("summary"),
                "description": event.get("description"),
                "start": (event.get("start") or {}).get("dateTime"),
                "end": (event.get("end") or {}).get("dateTime"),
            },
            detail=None,
        )

    except Exception as e:
        # aqui é erro "de negócio/google", não é 422 do pydantic
        return GoogleEventCreateOut(
            status="erro",
            motivo="Falha ao criar evento no Google Calendar",
            event=None,
            detail={"error": str(e)},
        )


@router.patch("/update", response_model=GoogleEventUpdateOut)
def update_google_event(payload: GoogleEventUpdateIn, db: Session = Depends(get_db)):
    try:
        # 1) garante token válido (faz refresh se necessário)
        access_token = GoogleTokenService.get_valid_access_token(db, payload.user_id)

        updated = google_calendar_service.update_event(
            access_token=access_token,  # <- string
            calendar_id=payload.calendar_id or "primary",
            event_id=payload.event_id,
            title=payload.summary,
            description=payload.description or "",
            start=payload.start_datetime,
            end=payload.end_datetime,
            timezone=payload.timezone or "America/Sao_Paulo",
        )

        return GoogleEventUpdateOut(
            status="ok",
            event={
                "id": updated.get("id"),
                "htmlLink": updated.get("htmlLink"),
                "calendar_id": payload.calendar_id or "primary",
                "summary": updated.get("summary"),
                "description": updated.get("description"),
                "start": (updated.get("start") or {}).get("dateTime"),
                "end": (updated.get("end") or {}).get("dateTime"),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        return GoogleEventUpdateOut(
            status="erro",
            motivo="Falha ao atualizar evento no Google Calendar",
            detail={"error": str(e)},
        )
        
# ---------------------------
# NOVO (para a Agenda - normalizado)
# ---------------------------

def _parse_iso(dt: str | None) -> datetime | None:
    if not dt:
        return None
    # aceita "2026-03-05T09:00:00-03:00"
    return datetime.fromisoformat(dt)


@router.get("/range", summary="(Novo) List por range - normalizado p/ Agenda")
def list_range_normalized(
    user_id: int = Query(...),
    calendar_id: str = Query("primary"),
    time_min: str | None = Query(None),
    time_max: str | None = Query(None),
    telefone: str | None = Query(None),
    db: Session = Depends(get_db),
):
    try:
        return google_calendar_events_crud.list_range(
            db=db,
            user_id=user_id,
            calendar_id=calendar_id,
            time_min=_parse_iso(time_min),
            time_max=_parse_iso(time_max),
            telefone=telefone,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("", summary="(Novo) Create - normalizado p/ Agenda")
def create_event_normalized(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """
    Espera:
    {
      "tenant_id": 21,
      "user_id": 60,
      "calendar_id": "primary",
      "title": "...",
      "description": "...",
      "location": "...",
      "start": "2026-03-05T09:00:00-03:00",
      "end": "2026-03-05T10:00:00-03:00",
      "timezone": "America/Sao_Paulo"
    }
    Retorna:
      {id,title,start,end,allDay,location,description}
    """
    try:
        return google_calendar_events_crud.create(
            db=db,
            user_id=payload["user_id"],
            calendar_id=payload.get("calendar_id") or "primary",
            title=payload.get("title") or "(Sem título)",
            description=payload.get("description"),
            location=payload.get("location"),
            start=payload["start"],
            end=payload["end"],
            timezone_str=payload.get("timezone") or "America/Sao_Paulo",
        )
    except KeyError as e:
        raise HTTPException(status_code=422, detail=f"Campo obrigatório ausente: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{event_id}", summary="(Novo) Update - normalizado p/ Agenda")
def update_event_normalized(
    event_id: str,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """
    Espera os mesmos campos do create (exceto id).
    """
    try:
        return google_calendar_events_crud.update(
            db=db,
            user_id=payload["user_id"],
            calendar_id=payload.get("calendar_id") or "primary",
            event_id=event_id,
            title=payload.get("title") or "(Sem título)",
            description=payload.get("description"),
            location=payload.get("location"),
            start=payload["start"],
            end=payload["end"],
            timezone_str=payload.get("timezone") or "America/Sao_Paulo",
        )
    except KeyError as e:
        raise HTTPException(status_code=422, detail=f"Campo obrigatório ausente: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
