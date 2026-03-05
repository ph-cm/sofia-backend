from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, Boolean
from app.db import Base

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    start_at = Column(DateTime, nullable=False, index=True)
    end_at = Column(DateTime, nullable=True)

    status = Column(String, nullable=False, default="scheduled")
    patient_name = Column(String, nullable=True)

    # opcionais p/ analytics
    amount_cents = Column(Integer, nullable=True)
    paid = Column(Boolean, nullable=True)