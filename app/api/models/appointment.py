from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, Boolean
from app.db.base_class import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=False)

    starts_at = Column(DateTime, index=True, nullable=False)  # era start_at
    ends_at = Column(DateTime, nullable=True)                 # era end_at

    status = Column(String, nullable=True)
    patient_name = Column(String, nullable=True)
    amount_cents = Column(Integer, nullable=True)
    paid = Column(Boolean, default=False)