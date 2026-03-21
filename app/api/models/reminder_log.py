from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from app.db.base_class import Base


class ReminderLog(Base):
    __tablename__ = "reminder_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    google_event_id = Column(String, nullable=False, index=True)
    tipo_lembrete = Column(String, nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())