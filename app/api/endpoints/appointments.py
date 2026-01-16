from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

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
