from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api.models.appointment import Appointment


def get_analytics_summary(db: Session, tenant_id: int, date_from: str, date_to: str):

    base = db.query(Appointment).filter(
        Appointment.tenant_id == tenant_id,
        Appointment.start_at >= date_from,
        Appointment.start_at <= date_to,
    )

    total = base.count()

    confirmed = base.filter(Appointment.status == "confirmed").count()
    completed = base.filter(Appointment.status == "completed").count()
    cancelled = base.filter(Appointment.status == "cancelled").count()
    no_show = base.filter(Appointment.status == "no_show").count()

    revenue = (
        db.query(func.sum(Appointment.amount))
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.status == "completed",
            Appointment.start_at >= date_from,
            Appointment.start_at <= date_to,
        )
        .scalar()
        or 0
    )

    avg_ticket = revenue / completed if completed else 0

    conversion = confirmed / total if total else 0

    breakdown = (
        db.query(
            Appointment.status,
            func.count(Appointment.id)
        )
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.start_at >= date_from,
            Appointment.start_at <= date_to,
        )
        .group_by(Appointment.status)
        .all()
    )

    recent = (
        db.query(Appointment)
        .filter(Appointment.tenant_id == tenant_id)
        .order_by(Appointment.start_at.desc())
        .limit(5)
        .all()
    )

    return {
        "kpis": {
            "totalAppointments": total,
            "confirmedAppointments": confirmed,
            "completedAppointments": completed,
            "cancelledAppointments": cancelled,
            "noShowAppointments": no_show,
            "grossRevenue": revenue,
            "pendingRevenue": 0,
            "avgTicket": avg_ticket,
            "conversionRate": conversion,
        },
        "breakdown": [
            {"status": s, "count": c}
            for s, c in breakdown
        ],
        "recent": [
            {
                "id": r.id,
                "patientName": r.patient_name,
                "startAt": r.start_at.isoformat(),
                "status": r.status,
            }
            for r in recent
        ],
    }