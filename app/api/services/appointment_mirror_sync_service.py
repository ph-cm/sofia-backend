# app/api/services/appointment_mirror_sync_service.py
from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session

from app.api.models.appointment import Appointment
from app.api.services.calendar_mirror import list_events_range


def _parse_iso_to_naive(s: str | None) -> datetime | None:
    if not s:
        return None
    if s.endswith("Z"):
        s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    return dt.replace(tzinfo=None)


class AppointmentMirrorSyncService:
    @staticmethod
    def sync_range_from_mirror(
        db: Session,
        *,
        tenant_id: int,
        user_id: int,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
        telefone: str | None = None,
    ) -> dict:
        events = list_events_range(
            db=db,
            user_id=user_id,
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
            telefone=telefone,
        )

        created = 0
        updated = 0

        for ev in events:
            google_event_id = ev.get("id")
            if not google_event_id:
                continue

            start_dt = _parse_iso_to_naive(ev.get("start"))
            end_dt = _parse_iso_to_naive(ev.get("end"))

            appt = (
                db.query(Appointment)
                .filter(Appointment.tenant_id == tenant_id)
                .filter(Appointment.google_event_id == google_event_id)
                .first()
            )

            if appt is None:
                appt = Appointment(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    calendar_id=calendar_id,
                    google_event_id=google_event_id,
                    telefone=telefone,
                )
                db.add(appt)
                created += 1
            else:
                updated += 1

            # ✅ nomes EXATOS do seu schema
            appt.start_datetime = start_dt
            appt.end_datetime = end_dt
            appt.summary = ev.get("title")
            appt.description = ev.get("description")
            # status do google não existe no seu espelho (e não vamos mexer nele)
            # então aqui você pode:
            # - manter status atual (se existir)
            # - OU setar um default quando criar
            if not appt.status:
                appt.status = "scheduled"

        db.commit()
        return {"total_events": len(events), "created": created, "updated": updated}