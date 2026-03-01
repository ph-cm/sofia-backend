from sqlalchemy import Boolean, Column, DateTime, BigInteger, Text, func, UniqueConstraint, Index
from app.db.base_class import Base


class FinanceCategory(Base):
    __tablename__ = "finance_categories"

    id = Column(BigInteger, primary_key=True, index=True)
    tenant_id = Column(BigInteger, nullable=False, index=True)

    name = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_fin_cat_tenant_name"),
        Index("idx_fin_cat_tenant", "tenant_id"),
    )