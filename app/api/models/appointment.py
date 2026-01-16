from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.db.base_class import Base
from typing import Optional

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, nullable=False)

    conversation_id: Optional[int] = None
    contact_id: Optional[int] = None
    telefone: Optional[str] = None

    calendar_id = Column(String, default="primary")
    google_event_id = Column(String, unique=True, nullable=False)

    start_datetime = Column(String, nullable=False)
    end_datetime = Column(String, nullable=False)

    summary = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    status = Column(String, default="confirmed")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
