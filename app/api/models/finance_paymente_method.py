from sqlalchemy import Boolean, Column, DateTime, BigInteger, Text, func
from app.db.base_class import Base

class FinancePaymentMethod(Base):
    __tablename__ = "finance_payment_methods"

    id = Column(BigInteger, primary_key=True, index=True)
    
    # tenant_id apagado! É uma constante global agora.

    name = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # __table_args__ apagado pois a restrição de unicidade não depende mais de tenant_id