from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.api.models.tenant import Tenant
from app.api.models.appointment import Appointment


class ReminderService:
    DEFAULT_CALENDAR_ID = "primary"
    DEFAULT_CADENCE_HOURS = [24, 12, 1]
    DEFAULT_TIMEZONE = "America/Sao_Paulo"

    @staticmethod
    def get_reminder_targets(db: Session) -> List[Dict[str, Any]]:
        tenants = (
            db.query(Tenant)
            .filter(Tenant.user_id.isnot(None))
            .filter(Tenant.chatwoot_account_id.isnot(None))
            .filter(Tenant.chatwoot_inbox_id.isnot(None))
            .filter(Tenant.evolution_instance_name.isnot(None))
            .all()
        )

        results: List[Dict[str, Any]] = []

        for tenant in tenants:
            results.append(
                {
                    "tenant_id": tenant.id,
                    "user_id": tenant.user_id,
                    "tenant_name": tenant.name,
                    "calendar_id": ReminderService.DEFAULT_CALENDAR_ID,
                    "chatwoot_account_id": tenant.chatwoot_account_id,
                    "chatwoot_inbox_id": tenant.chatwoot_inbox_id,
                    "evolution_instance_name": tenant.evolution_instance_name,
                    "cadence_hours": ReminderService.DEFAULT_CADENCE_HOURS,
                    "timezone": ReminderService.DEFAULT_TIMEZONE,
                    "enabled": True,
                }
            )

        return results

    @staticmethod
    def get_upcoming_appointments(
        db: Session,
        *,
        user_id: int,
        after: datetime,
        before: datetime,
    ) -> List[Dict[str, Any]]:
        after = ReminderService._normalize_dt(after)
        before = ReminderService._normalize_dt(before)

        query = (
            db.query(Appointment)
            .filter(Appointment.user_id == user_id)
            .filter(Appointment.start_datetime >= after)
            .filter(Appointment.start_datetime <= before)
        )

        if hasattr(Appointment, "status"):
            query = query.filter(Appointment.status != "cancelled")

        appointments = query.order_by(Appointment.start_datetime.asc()).all()

        results: List[Dict[str, Any]] = []

        for appt in appointments:
            phone = ReminderService._extract_phone(appt)
            start_dt = ReminderService._extract_start_datetime(appt)
            end_dt = ReminderService._extract_end_datetime(appt)
            patient_name = ReminderService._extract_patient_name(appt)

            if not phone:
                continue

            results.append(
                {
                    "appointment_id": appt.id,
                    "user_id": user_id,
                    "google_event_id": getattr(appt, "google_event_id", None),
                    "start_datetime": start_dt.isoformat(),
                    "end_datetime": end_dt.isoformat() if end_dt else None,
                    "patient_name": patient_name,
                    "telefone": phone,
                }
            )

        return results

    @staticmethod
    def mark_reminder_sent(
        db: Session,
        *,
        appointment_id: int,
        tipo_lembrete: str,
        sent_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        return {
            "success": True,
            "appointment_id": appointment_id,
            "tipo_lembrete": tipo_lembrete,
            "sent_at": ReminderService._normalize_dt(
                sent_at or datetime.now(timezone.utc)
            ).isoformat(),
        }

    @staticmethod
    def _extract_phone(appt: Appointment) -> Optional[str]:
        possible_fields = [
            "telefone",
            "phone",
            "patient_phone",
            "contact_phone",
        ]

        for field in possible_fields:
            if hasattr(appt, field):
                value = getattr(appt, field)
                if value:
                    return str(value)

        return None

    @staticmethod
    def _extract_patient_name(appt: Appointment) -> str:
        possible_fields = [
            "patient_name",
            "nome_paciente",
            "title",
            "titulo",
        ]

        for field in possible_fields:
            if hasattr(appt, field):
                value = getattr(appt, field)
                if value:
                    return str(value)

        return "Paciente"

    @staticmethod
    def _extract_start_datetime(appt: Appointment) -> datetime:
        possible_fields = [
            "start_datetime",
            "evento_inicio",
            "starts_at",
            "start_at",
        ]

        for field in possible_fields:
            if hasattr(appt, field):
                value = getattr(appt, field)
                if value:
                    return ReminderService._normalize_dt(value)

        raise ValueError("Appointment sem campo de início reconhecido")

    @staticmethod
    def _extract_end_datetime(appt: Appointment) -> Optional[datetime]:
        possible_fields = [
            "end_datetime",
            "evento_fim",
            "ends_at",
            "end_at",
        ]

        for field in possible_fields:
            if hasattr(appt, field):
                value = getattr(appt, field)
                if value:
                    return ReminderService._normalize_dt(value)

        return None

    @staticmethod
    def _normalize_dt(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value