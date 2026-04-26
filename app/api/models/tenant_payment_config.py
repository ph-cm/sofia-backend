from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.base_class import Base


class TenantPaymentConfig(Base):
    __tablename__ = "tenant_payment_config"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False, index=True, unique=True)
    deposit_per_child = Column(Integer, nullable=False)
    card_link_1_child = Column(String, nullable=True)
    card_link_2_children = Column(String, nullable=True)
    pix_key = Column(String, nullable=False)
    pix_name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
