# app/api/services/appointment_service.py
from sqlalchemy.orm import Session
from app.api.models.appointment import Appointment

class AppointmentService:

    @staticmethod
    def create(db: Session, payload: dict) -> Appointment:
        appointment = Appointment(**payload)
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
        return appointment

    @staticmethod
    def get_by_conversation(
        db: Session,
        user_id: int,
        conversation_id: str
    ) -> Appointment | None:
        return (
            db.query(Appointment)
            .filter(
                Appointment.user_id == user_id,
                Appointment.conversation_id == conversation_id,
                Appointment.status == "confirmed",
            )
            .order_by(Appointment.created_at.desc())
            .first()
        )

    @staticmethod
    def cancel(db: Session, appointment: Appointment):
        appointment.status = "cancelled"
        db.commit()
        db.refresh(appointment)
        return appointment
