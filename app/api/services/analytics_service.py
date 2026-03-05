from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.api.models.appointment import Appointment
from app.api.models.tenant import Tenant


class AnalyticsService:

    @staticmethod
    def summary(db: Session, tenant_id: int, date_from: date, date_to: date):

        start_dt = datetime.combine(date_from, datetime.min.time())
        end_dt = datetime.combine(date_to, datetime.max.time())

        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant não encontrado")

        # 🔹 agora filtra diretamente pelo tenant_id
        rows = (
            db.query(Appointment)
            .filter(Appointment.tenant_id == tenant_id)
            .filter(Appointment.start_datetime >= start_dt)
            .filter(Appointment.start_datetime <= end_dt)
            .all()
        )

        statuses = ["scheduled", "confirmed", "completed", "cancelled", "no_show"]

        counts = {s: 0 for s in statuses}

        for a in rows:
            status = a.status or "scheduled"

            if status not in counts:
                counts[status] = 0

            counts[status] += 1

        total = sum(counts.values())

        confirmed = counts.get("confirmed", 0)
        completed = counts.get("completed", 0)
        cancelled = counts.get("cancelled", 0)
        no_show = counts.get("no_show", 0)

        conversion = (confirmed / total) if total > 0 else 0

        # ---------------- RECENTES ----------------

        recent_rows = sorted(rows, key=lambda x: x.start_datetime, reverse=True)[:10]

        recent = []

        for a in recent_rows:
            recent.append({
                "id": a.id,
                "patientName": a.summary,
                "startAt": a.start_datetime.isoformat(),
                "status": a.status,
            })

        # ---------------- TIMESERIES ----------------

        day_map = {}

        current = date_from

        while current <= date_to:

            key = current.isoformat()

            day_map[key] = {
                "day": key,
                "total": 0,
                "completed": 0,
                "cancelled": 0,
            }

            current += timedelta(days=1)

        for a in rows:

            day = a.start_datetime.date().isoformat()

            if day not in day_map:
                continue

            day_map[day]["total"] += 1

            if a.status == "completed":
                day_map[day]["completed"] += 1

            if a.status == "cancelled":
                day_map[day]["cancelled"] += 1

        timeseries = list(day_map.values())

        return {
            "tenant_id": tenant_id,
            "from": date_from.isoformat(),
            "to": date_to.isoformat(),
            "kpis": {
                "totalAppointments": total,
                "confirmedAppointments": confirmed,
                "completedAppointments": completed,
                "cancelledAppointments": cancelled,
                "noShowAppointments": no_show,
                "newPatients": 0,
                "avgConsultTimeMin": 0,
                "grossRevenueCents": 0,
                "pendingRevenueCents": 0,
                "conversionRate": conversion,
            },
            "breakdown": [
                {"status": status, "count": counts.get(status, 0)}
                for status in statuses
            ],
            "recent": recent,
            "timeseries": timeseries,
        }