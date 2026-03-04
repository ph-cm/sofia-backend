from sqlalchemy import Boolean, Column, DateTime, BigInteger, Text, func
from app.db.base_class import Base

class FinanceCategory(Base):
    __tablename__ = "finance_categories"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)