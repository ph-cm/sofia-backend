from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.services.reminder_service import ReminderService

router = APIRouter(prefix="/reminders", tags=["Reminders"])


class MarkReminderSentRequest(BaseModel):
    appointment_id: int
    tipo_lembrete: str
    sent_at: Optional[datetime] = None


@router.get("/targets")
def get_reminder_targets(db: Session = Depends(get_db)):
    return ReminderService.get_reminder_targets(db)


@router.get("/upcoming-appointments")
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


@router.post("/mark-sent")
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