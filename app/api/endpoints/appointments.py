from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from app.db.session import get_db
from app.api.services.appointment_service import AppointmentService
from app.api.models.appointment import Appointment

router = APIRouter(prefix="/appointments", tags=["appointments"])

@router.post("/create")
def create_appointment(
    payload: dict,
    db: Session = Depends(get_db),
):
    """
    Registra no banco um agendamento já criado no Google Calendar.
    """
    try:
        appointment = AppointmentService.create(db, payload)
        return {
            "status": "ok",
            "appointment_id": appointment.id,
            "google_event_id": appointment.google_event_id,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/lookup")
def lookup_appointment(
    user_id: int,
    conversation_id: str,
    db: Session = Depends(get_db),
):
    """
    Retorna o último agendamento ativo de uma conversa.
    """
    appointment = AppointmentService.get_by_conversation(
        db=db,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Nenhum agendamento ativo encontrado para esta conversa",
        )

    return {
        "status": "ok",
        "appointment": {
            "appointment_id": appointment.id,
            "google_event_id": appointment.google_event_id,
            "calendar_id": appointment.calendar_id,
            "start": appointment.start_datetime,
            "end": appointment.end_datetime,
            "summary": appointment.summary,
            "status": appointment.status,
        },
    }

@router.post("/cancel")
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
):
    appointment = db.query(Appointment).get(appointment_id)

    if not appointment:
        raise HTTPException(404, "Agendamento não encontrado")

    AppointmentService.cancel(db, appointment)

    return {
        "status": "cancelled",
        "appointment_id": appointment.id,
    }

class AppointmentAttachContextIn(BaseModel):
    user_id: int = Field(..., ge=1)
    calendar_id: str = "primary"
    event_id: str

    conversation_id: str
    contact_id: str
    telefone_contato: Optional[str] = None

    start_datetime: str
    end_datetime: str
    summary: Optional[str] = None
    description: Optional[str] = None
    
@router.post("/attach-context")
def attach_context(payload: AppointmentAttachContextIn, db: Session = Depends(get_db)):
    # upsert por (user_id + event_id)
    appt = (
        db.query(Appointment)
        .filter(Appointment.user_id == payload.user_id, Appointment.event_id == payload.event_id)
        .first()
    )

    if not appt:
        appt = Appointment(
            user_id=payload.user_id,
            event_id=payload.event_id,
        )
        db.add(appt)

    appt.calendar_id = payload.calendar_id
    appt.conversation_id = payload.conversation_id
    appt.contact_id = payload.contact_id
    appt.telefone_contato = payload.telefone_contato
    appt.start_datetime = payload.start_datetime
    appt.end_datetime = payload.end_datetime
    appt.summary = payload.summary
    appt.description = payload.description
    appt.status = "scheduled"

    db.commit()
    db.refresh(appt)

    return {
        "status": "ok",
        "appointment": {
            "id": appt.id,
            "user_id": appt.user_id,
            "event_id": appt.event_id,
            "calendar_id": appt.calendar_id,
            "conversation_id": appt.conversation_id,
            "contact_id": appt.contact_id,
            "telefone_contato": appt.telefone_contato,
            "start_datetime": appt.start_datetime,
            "end_datetime": appt.end_datetime,
            "status": appt.status,
        }
    }