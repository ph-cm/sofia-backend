from sqlalchemy import Column, Integer, String, DateTime
from app.db import Base

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True)

    tenant_id = Column(Integer, index=True)
    user_id = Column(Integer)

    conversation_id = Column(Integer)
    contact_id = Column(Integer)

    telefone = Column(String)

    calendar_id = Column(String)
    google_event_id = Column(String)

    start_datetime = Column(DateTime)   # ← ESSA LINHA É A QUE FALTA
    end_datetime = Column(DateTime)     # ← ESSA TAMBÉM

    summary = Column(String)
    description = Column(String)

    status = Column(String)

    created_at = Column(DateTime)
    updated_at = Column(DateTime)