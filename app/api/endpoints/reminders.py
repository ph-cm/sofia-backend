from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.services.reminder_service import ReminderService

router = APIRouter(prefix="/reminders", tags=["Reminders"])


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
    appointment_id: int
    tipo_lembrete: str
    sent_at: Optional[datetime] = None


class MarkReminderSentResponse(BaseModel):
    success: bool
    appointment_id: int
    tipo_lembrete: str
    sent_at: str


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


@router.post("/mark-sent", response_model=MarkReminderSentResponse)
def mark_reminder_sent(
    payload: MarkReminderSentRequest,
    db: Session = Depends(get_db),
):
    return ReminderService.mark_reminder_sent(
        db,
        appointment_id=payload.appointment_id,
        tipo_lembrete=payload.tipo_lembrete,
        sent_at=payload.sent_at,
    )