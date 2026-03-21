from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.services.reminder_service import ReminderService
from app.api.models.appointment import Appointment

router = APIRouter(prefix="/reminders", tags=["Reminders"])


class GoogleEventResponse(BaseModel):
    google_event_id: Optional[str] = None
    status: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    html_link: Optional[str] = None


class ReminderTargetResponse(BaseModel):
    tenant_id: int
    user_id: int
    tenant_name: str
    calendar_id: str
    chatwoot_account_id: int
    chatwoot_inbox_id: int
    evolution_instance_name: str
    cadence_hours: List[int]
    timezone: str
    enabled: bool


class UpcomingAppointmentResponse(BaseModel):
    appointment_id: int
    user_id: int
    google_event_id: Optional[str] = None
    start_datetime: str
    end_datetime: Optional[str] = None
    patient_name: str
    telefone: str


class MarkReminderSentRequest(BaseModel):
    user_id: int
    google_event_id: str
    tipo_lembrete: str
    sent_at: Optional[datetime] = None


class MarkReminderSentResponse(BaseModel):
    success: bool
    already_sent: bool
    user_id: int
    google_event_id: str
    tipo_lembrete: str
    sent_at: str


class ReminderAlreadySentResponse(BaseModel):
    already_sent: bool
    user_id: int
    google_event_id: str
    tipo_lembrete: str
    sent_at: Optional[str] = None

class GoogleEventChangedResponse(BaseModel):
    change_type: str
    user_id: int
    google_event_id: str
    summary: Optional[str] = None
    description: Optional[str] = None
    old_start_datetime: Optional[str] = None
    new_start_datetime: Optional[str] = None
    old_end_datetime: Optional[str] = None
    new_end_datetime: Optional[str] = None
    status: Optional[str] = None
    
@router.get("/google-events", response_model=List[GoogleEventResponse])
def get_google_events(
    user_id: int = Query(...),
    after: datetime = Query(...),
    before: datetime = Query(...),
    db: Session = Depends(get_db),
):
    return ReminderService.get_google_events(
        db,
        user_id=user_id,
        after=after,
        before=before,
    )


@router.get("/debug-appointments-by-user")
def debug_appointments_by_user(
    user_id: int,
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    appointments = (
        db.query(Appointment)
        .filter(Appointment.user_id == user_id)
        .limit(20)
        .all()
    )

    results = []

    for appt in appointments:
        results.append(
            {
                "id": getattr(appt, "id", None),
                "user_id": getattr(appt, "user_id", None),
                "tenant_id": getattr(appt, "tenant_id", None),
                "status": getattr(appt, "status", None),
                "start_datetime": str(getattr(appt, "start_datetime", None)),
                "evento_inicio": str(getattr(appt, "evento_inicio", None)),
                "starts_at": str(getattr(appt, "starts_at", None)),
                "patient_name": getattr(appt, "patient_name", None),
                "nome_paciente": getattr(appt, "nome_paciente", None),
                "title": getattr(appt, "title", None),
                "telefone": getattr(appt, "telefone", None),
                "phone": getattr(appt, "phone", None),
                "patient_phone": getattr(appt, "patient_phone", None),
            }
        )

    return results


@router.get("/debug-appointments")
def debug_appointments(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    appointments = db.query(Appointment).limit(20).all()

    results = []

    for appt in appointments:
        results.append(
            {
                "id": getattr(appt, "id", None),
                "user_id": getattr(appt, "user_id", None),
                "tenant_id": getattr(appt, "tenant_id", None),
                "status": getattr(appt, "status", None),
                "start_datetime": str(getattr(appt, "start_datetime", None)),
                "end_datetime": str(getattr(appt, "end_datetime", None)),
                "evento_inicio": str(getattr(appt, "evento_inicio", None)),
                "evento_fim": str(getattr(appt, "evento_fim", None)),
                "starts_at": str(getattr(appt, "starts_at", None)),
                "end_at": str(getattr(appt, "end_at", None)),
                "patient_name": getattr(appt, "patient_name", None),
                "nome_paciente": getattr(appt, "nome_paciente", None),
                "title": getattr(appt, "title", None),
                "telefone": getattr(appt, "telefone", None),
                "phone": getattr(appt, "phone", None),
                "patient_phone": getattr(appt, "patient_phone", None),
                "contact_phone": getattr(appt, "contact_phone", None),
                "google_event_id": getattr(appt, "google_event_id", None),
            }
        )

    return results


@router.get("/targets", response_model=List[ReminderTargetResponse])
def get_reminder_targets(db: Session = Depends(get_db)):
    return ReminderService.get_reminder_targets(db)


@router.get("/upcoming-appointments", response_model=List[UpcomingAppointmentResponse])
def get_upcoming_appointments(
    user_id: int = Query(...),
    after: datetime = Query(...),
    before: datetime = Query(...),
    db: Session = Depends(get_db),
):
    return ReminderService.get_upcoming_appointments(
        db,
        user_id=user_id,
        after=after,
        before=before,
    )


@router.get("/already-sent", response_model=ReminderAlreadySentResponse)
def was_reminder_sent(
    user_id: int = Query(...),
    google_event_id: str = Query(...),
    tipo_lembrete: str = Query(...),
    db: Session = Depends(get_db),
):
    return ReminderService.was_reminder_sent(
        db,
        user_id=user_id,
        google_event_id=google_event_id,
        tipo_lembrete=tipo_lembrete,
    )


@router.post("/mark-sent", response_model=MarkReminderSentResponse)
def mark_reminder_sent(
    payload: MarkReminderSentRequest,
    db: Session = Depends(get_db),
):
    return ReminderService.mark_reminder_sent(
        db,
        user_id=payload.user_id,
        google_event_id=payload.google_event_id,
        tipo_lembrete=payload.tipo_lembrete,
        sent_at=payload.sent_at,
    )
    
@router.get("/google-events-changed", response_model=List[GoogleEventChangedResponse])
def get_google_events_changed(
    user_id: int = Query(...),
    after: datetime = Query(...),
    before: datetime = Query(...),
    db: Session = Depends(get_db),
):
    return ReminderService.get_google_events_changed(
        db,
        user_id=user_id,
        after=after,
        before=before,
    )