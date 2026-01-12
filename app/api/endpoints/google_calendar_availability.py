from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import requests

from app.db.session import get_db
from app.api.services.google_token_service import GoogleTokenService

router = APIRouter(prefix="/google", tags=["Google Calendar"])

# ============================
# Pydantic Request Model
# ============================

class AvailabilityRequest(BaseModel):
    user_id: int = Field(..., description="ID do usuário dono das credenciais")
    calendar_id: str = Field("primary", description="ID do calendário")
    start_date: str = Field(..., description="ISO datetime início (RFC3339)")
    end_date: str = Field(..., description="ISO datetime fim (RFC3339)")
    timezone: str = Field("America/Sao_Paulo", description="Fuso horário do usuário")


# ============================
# Google FreeBusy Endpoint
# ============================

@router.post("/availability")
def check_calendar_availability(payload: AvailabilityRequest, db: Session = Depends(get_db)):

    # 1. Buscar token válido (renova automaticamente se expirado)
    try:
        access_token = GoogleTokenService.get_valid_access_token(
            db,
            payload.user_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Preparar corpo da requisição FreeBusy
    freebusy_body = {
        "timeMin": payload.start_date,
        "timeMax": payload.end_date,
        "timeZone": payload.timezone,
        "items": [{"id": payload.calendar_id}],
    }

    # 3. Chamar Google Calendar API
    response = requests.post(
        "https://www.googleapis.com/calendar/v3/freeBusy",
        headers={"Authorization": f"Bearer {access_token}"},
        json=freebusy_body
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao consultar disponibilidade: {response.text}"
        )

    data = response.json()

    # 4. Formatar resposta final
    calendar_data = data.get("calendars", {}).get(payload.calendar_id, {})
    busy_slots = calendar_data.get("busy", [])

    return {
        "calendar_id": payload.calendar_id,
        "is_available": len(busy_slots) == 0,
        "busy_slots": busy_slots,
        "start": payload.start_date,
        "end": payload.end_date
    }
