# app/api/services/analytics_service.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

# ajuste esses imports pro seu projeto:
from app.api.models.appointment import Appointment  # se o model for outro nome, troque
from app.api.models.user import User                # opcional (newPatients)
from app.api.models.finance_transaction import FinanceTransaction  # opcional (receita)


@dataclass
class AnalyticsService:
    @staticmethod
    def summary(db: Session, tenant_id: int, date_from: date, date_to: date) -> Dict[str, Any]:
        """
        Retorna o shape que o frontend espera.
        - tenant_id
        - from/to
        - kpis
        - breakdown
        - recent
        - timeseries (opcional)
        """

        # intervalo [from 00:00, to 23:59:59]
        start_dt = datetime.combine(date_from, datetime.min.time())
        end_dt = datetime.combine(date_to, datetime.max.time())

        # ------------- APPOINTMENTS -------------
        q = (
            db.query(Appointment)
            .filter(Appointment.tenant_id == tenant_id)
            .filter(Appointment.start_at >= start_dt)
            .filter(Appointment.start_at <= end_dt)
        )

        rows: List[Appointment] = q.all()

        def status_of(a: Appointment) -> str:
            # ajuste se seu campo tiver outro nome
            return getattr(a, "status", "scheduled") or "scheduled"

        # breakdown
        statuses = ["scheduled", "confirmed", "completed", "cancelled", "no_show"]
        counts = {s: 0 for s in statuses}

        for a in rows:
            s = status_of(a)
            if s not in counts:
                # evita quebrar se houver status novo
                counts[s] = 0
            counts[s] += 1

        total = sum(counts.values())

        confirmed = counts.get("confirmed", 0)
        completed = counts.get("completed", 0)
        cancelled = counts.get("cancelled", 0)
        no_show = counts.get("no_show", 0)

        conversion = (confirmed / total) if total > 0 else 0.0

        # ------------- RECEITA (opcional) -------------
        # Se você ainda não tem transação ligada à consulta, deixa 0 e evolui depois.
        gross_cents = 0
        pending_cents = 0

        # EXEMPLO se você tiver FinanceTransaction com tenant_id e status:
        # paid = soma paid
        # pending = soma pending
        try:
            paid_sum = (
                db.query(FinanceTransaction)
                .filter(FinanceTransaction.tenant_id == tenant_id)
                .filter(FinanceTransaction.kind == "income")
                .filter(FinanceTransaction.status == "paid")
                .filter(FinanceTransaction.created_at >= start_dt)
                .filter(FinanceTransaction.created_at <= end_dt)
                .with_entities(FinanceTransaction.amount_cents)
                .all()
            )
            gross_cents = sum(x[0] or 0 for x in paid_sum)

            pend_sum = (
                db.query(FinanceTransaction)
                .filter(FinanceTransaction.tenant_id == tenant_id)
                .filter(FinanceTransaction.kind == "income")
                .filter(FinanceTransaction.status == "pending")
                .filter(FinanceTransaction.created_at >= start_dt)
                .filter(FinanceTransaction.created_at <= end_dt)
                .with_entities(FinanceTransaction.amount_cents)
                .all()
            )
            pending_cents = sum(x[0] or 0 for x in pend_sum)
        except Exception:
            # se não existe tabela/model ainda, segue com 0
            gross_cents = 0
            pending_cents = 0

        # ------------- NEW PATIENTS + AVG TIME (opcional) -------------
        new_patients = 0
        avg_time_min = 0

        # Se suas consultas guardam patient_id e end_at:
        try:
            patient_ids = {getattr(a, "patient_id", None) for a in rows if getattr(a, "patient_id", None)}
            # newPatients ideal = pacientes cuja primeira consulta no consultório cai no período
            # (isso exige query mais elaborada; por enquanto: pacientes distintos no período)
            new_patients = len(patient_ids)

            durations = []
            for a in rows:
                st = getattr(a, "start_at", None)
                en = getattr(a, "end_at", None)
                if st and en:
                    durations.append((en - st).total_seconds() / 60)
            avg_time_min = int(round(sum(durations) / len(durations))) if durations else 0
        except Exception:
            new_patients = 0
            avg_time_min = 0

        # ------------- RECENT -------------
        recent = sorted(rows, key=lambda a: getattr(a, "start_at"), reverse=True)[:10]
        recent_payload = []
        for a in recent:
            recent_payload.append(
                {
                    "id": getattr(a, "id"),
                    "patientName": getattr(a, "patient_name", None),  # ajuste
                    "startAt": getattr(a, "start_at").isoformat(),
                    "status": status_of(a),
                    "amountCents": getattr(a, "amount_cents", None),
                    "paid": getattr(a, "paid", None),
                }
            )

        # ------------- TIMESERIES (opcional) -------------
        # total/completed/cancelled por dia
        day_map = {}
        cur = date_from
        while cur <= date_to:
            day_map[cur.isoformat()] = {"day": cur.isoformat(), "total": 0, "completed": 0, "cancelled": 0}
            cur += timedelta(days=1)

        for a in rows:
            d = getattr(a, "start_at").date().isoformat()
            if d not in day_map:
                day_map[d] = {"day": d, "total": 0, "completed": 0, "cancelled": 0}
            day_map[d]["total"] += 1
            s = status_of(a)
            if s == "completed":
                day_map[d]["completed"] += 1
            if s == "cancelled":
                day_map[d]["cancelled"] += 1

        timeseries = [day_map[k] for k in sorted(day_map.keys())]

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
                "newPatients": new_patients,
                "avgConsultTimeMin": avg_time_min,
                "grossRevenueCents": gross_cents,
                "pendingRevenueCents": pending_cents,
                "conversionRate": conversion,
            },
            "breakdown": [{"status": s, "count": counts.get(s, 0)} for s in statuses],
            "recent": recent_payload,
            "timeseries": timeseries,
        }