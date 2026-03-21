from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.api.models.tenant import Tenant
from app.api.models.appointment import Appointment
from app.api.models.google_token import GoogleToken
from app.api.models.user import User
from app.api.models.reminder_log import ReminderLog
from app.api.services.google_service import GoogleAuthService


class ReminderService:
    DEFAULT_CALENDAR_ID = "primary"
    DEFAULT_CADENCE_HOURS = [24, 12, 1]
    DEFAULT_TIMEZONE = "America/Sao_Paulo"

    @staticmethod
    def get_google_events(
        db: Session,
        *,
        user_id: int,
        after: datetime,
        before: datetime,
    ) -> List[Dict[str, Any]]:
        after = ReminderService._normalize_dt(after)
        before = ReminderService._normalize_dt(before)

        tenant = (
            db.query(Tenant)
            .filter(Tenant.user_id == user_id)
            .first()
        )

        if not tenant:
            raise ValueError(f"Tenant não encontrado para user_id={user_id}")

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:
            raise ValueError(f"User não encontrado para user_id={user_id}")

        google_token = (
            db.query(GoogleToken)
            .filter(GoogleToken.user_id == user_id)
            .first()
        )

        if not google_token:
            raise ValueError(f"GoogleToken não encontrado para user_id={user_id}")

        access_token = google_token.google_access_token
        refresh_token = google_token.google_refresh_token
        expires_at = google_token.google_token_expiry
        calendar_id = getattr(user, "calendar_id", None) or ReminderService.DEFAULT_CALENDAR_ID

        if not access_token:
            raise ValueError(f"user_id={user_id} sem access token Google")

        if not refresh_token:
            raise ValueError(f"user_id={user_id} sem refresh token Google")

        google_service = GoogleAuthService()

        token_data = google_service.refresh_access_token_if_needed(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )

        access_token = token_data["access_token"]
        new_expires_at = token_data["expires_at"]

        if token_data["refreshed"]:
            google_token.google_access_token = access_token
            google_token.google_token_expiry = new_expires_at
            db.add(google_token)
            db.commit()
            db.refresh(google_token)

        try:
            payload = google_service.list_calendar_events(
                access_token=access_token,
                calendar_id=calendar_id,
                time_min=after.isoformat(),
                time_max=before.isoformat(),
                max_results=100,
            )
        except PermissionError:
            refreshed = google_service.refresh_access_token(
                access_token=access_token,
                refresh_token=refresh_token,
            )

            access_token = refreshed["access"]
            new_expires_at = refreshed["expiry"]

            google_token.google_access_token = access_token
            google_token.google_token_expiry = new_expires_at
            db.add(google_token)
            db.commit()
            db.refresh(google_token)

            payload = google_service.list_calendar_events(
                access_token=access_token,
                calendar_id=calendar_id,
                time_min=after.isoformat(),
                time_max=before.isoformat(),
                max_results=100,
            )

        items = payload.get("items", [])
        results: List[Dict[str, Any]] = []

        for item in items:
            status = item.get("status")
            if status == "cancelled":
                continue

            start_raw = item.get("start", {})
            end_raw = item.get("end", {})

            start_dt = start_raw.get("dateTime") or start_raw.get("date")
            end_dt = end_raw.get("dateTime") or end_raw.get("date")

            results.append(
                {
                    "google_event_id": item.get("id"),
                    "status": status,
                    "summary": item.get("summary"),
                    "description": item.get("description"),
                    "start_datetime": start_dt,
                    "end_datetime": end_dt,
                    "html_link": item.get("htmlLink"),
                }
            )

        return results

    @staticmethod
    def get_reminder_targets(db: Session) -> List[Dict[str, Any]]:
        tenants = (
            db.query(Tenant)
            .filter(Tenant.user_id.isnot(None))
            .filter(Tenant.chatwoot_account_id.isnot(None))
            .filter(Tenant.evolution_instance_name.isnot(None))
            .all()
        )

        results: List[Dict[str, Any]] = []

        for tenant in tenants:
            user = (
                db.query(User)
                .filter(User.id == tenant.user_id)
                .first()
            )

            if not user:
                continue

            if not getattr(user, "ativo", False):
                continue

            if not getattr(user, "inbox_id", None):
                continue

            if not getattr(user, "calendar_id", None):
                continue

            google_token = (
                db.query(GoogleToken)
                .filter(GoogleToken.user_id == tenant.user_id)
                .first()
            )

            if not google_token:
                continue

            if not google_token.google_access_token:
                continue

            if not google_token.google_refresh_token:
                continue

            results.append(
                {
                    "tenant_id": tenant.id,
                    "user_id": user.id,
                    "tenant_name": tenant.name,
                    "calendar_id": user.calendar_id,
                    "chatwoot_account_id": tenant.chatwoot_account_id,
                    "chatwoot_inbox_id": user.inbox_id,
                    "evolution_instance_name": tenant.evolution_instance_name,
                    "cadence_hours": ReminderService.DEFAULT_CADENCE_HOURS,
                    "timezone": user.timezone or ReminderService.DEFAULT_TIMEZONE,
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

        appointments = (
            db.query(Appointment)
            .filter(Appointment.user_id == user_id)
            .all()
        )

        if hasattr(Appointment, "status"):
            appointments = [
                appt for appt in appointments
                if getattr(appt, "status", None) != "cancelled"
            ]

        filtered_appointments: List[Appointment] = []

        for appt in appointments:
            start_dt = ReminderService._extract_start_datetime(appt)
            if after <= start_dt <= before:
                filtered_appointments.append(appt)

        appointments = sorted(
            filtered_appointments,
            key=lambda x: ReminderService._extract_start_datetime(x),
        )

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
    def was_reminder_sent(
        db: Session,
        *,
        user_id: int,
        google_event_id: str,
        tipo_lembrete: str,
    ) -> Dict[str, Any]:
        existing = (
            db.query(ReminderLog)
            .filter(ReminderLog.user_id == user_id)
            .filter(ReminderLog.google_event_id == google_event_id)
            .filter(ReminderLog.tipo_lembrete == tipo_lembrete)
            .first()
        )

        return {
            "already_sent": existing is not None,
            "user_id": user_id,
            "google_event_id": google_event_id,
            "tipo_lembrete": tipo_lembrete,
            "sent_at": existing.sent_at.isoformat() if existing else None,
        }

    @staticmethod
    def mark_reminder_sent(
        db: Session,
        *,
        user_id: int,
        google_event_id: str,
        tipo_lembrete: str,
        sent_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        sent_at = ReminderService._normalize_dt(sent_at or datetime.now(timezone.utc))

        existing = (
            db.query(ReminderLog)
            .filter(ReminderLog.user_id == user_id)
            .filter(ReminderLog.google_event_id == google_event_id)
            .filter(ReminderLog.tipo_lembrete == tipo_lembrete)
            .first()
        )

        if existing:
            return {
                "success": True,
                "already_sent": True,
                "user_id": user_id,
                "google_event_id": google_event_id,
                "tipo_lembrete": tipo_lembrete,
                "sent_at": existing.sent_at.isoformat(),
            }

        log = ReminderLog(
            user_id=user_id,
            google_event_id=google_event_id,
            tipo_lembrete=tipo_lembrete,
            sent_at=sent_at,
        )

        db.add(log)
        db.commit()
        db.refresh(log)

        return {
            "success": True,
            "already_sent": False,
            "user_id": user_id,
            "google_event_id": google_event_id,
            "tipo_lembrete": tipo_lembrete,
            "sent_at": log.sent_at.isoformat(),
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