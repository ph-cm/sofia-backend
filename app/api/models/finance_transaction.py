from sqlalchemy import (
    Column,
    Date,
    DateTime,
    BigInteger,
    Text,
    func,
    Index,
    ForeignKey,
)
from app.db.base_class import Base


class FinanceTransaction(Base):
    __tablename__ = "finance_transactions"

    id = Column(BigInteger, primary_key=True, index=True)

    tenant_id = Column(BigInteger, nullable=False, index=True)
    created_by_user_id = Column(BigInteger, nullable=False, index=True)

    # 'income' | 'expense'
    kind = Column(Text, nullable=False)

    # 'pending' | 'paid' | 'cancelled'
    status = Column(Text, nullable=False)

    amount_cents = Column(BigInteger, nullable=False)
    currency = Column(Text, nullable=False, default="BRL")

    category_id = Column(BigInteger, ForeignKey("finance_categories.id", ondelete="SET NULL"), nullable=True)
    payment_method_id = Column(BigInteger, ForeignKey("finance_payment_methods.id", ondelete="SET NULL"), nullable=True)

    patient_name = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    due_date = Column(Date, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    # futuro (integra agenda/appointments depois)
    appointment_id = Column(BigInteger, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_fin_tx_tenant_created", "tenant_id", "created_at"),
        Index("idx_fin_tx_tenant_due", "tenant_id", "due_date"),
        Index("idx_fin_tx_tenant_status", "tenant_id", "status"),
        Index("idx_fin_tx_tenant_kind", "tenant_id", "kind"),
    )