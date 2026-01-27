from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class TenantIntegration(Base):
    __tablename__ = "tenant_integrations"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_tenant_integrations_user_id"),
        UniqueConstraint("chatwoot_account_id", name="uq_tenant_integrations_chatwoot_account_id"),
        UniqueConstraint("chatwoot_inbox_id", name="uq_tenant_integrations_chatwoot_inbox_id"),
        UniqueConstraint("evolution_instance_id", name="uq_tenant_integrations_evolution_instance_id"),
    )

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Chatwoot
    chatwoot_account_id = Column(Integer, nullable=True)
    chatwoot_inbox_id = Column(Integer, nullable=True)
    chatwoot_inbox_identifier = Column(String, nullable=True)  # token "inbox_identifier"

    # Evolution
    evolution_instance_id = Column(String, nullable=True)  # ex: tenant_123
    evolution_phone = Column(String, nullable=True)        # numero conectado (E.164) se quiser salvar

    user = relationship("User")
