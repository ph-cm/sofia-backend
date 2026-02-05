from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime, func
from app.db.base_class import Base  # ajuste: onde fica seu declarative_base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    # Evolution
    evolution_instance_name = Column(String, unique=True, index=True, nullable=True)

    # Chatwoot (dinâmico por tenant)
    chatwoot_account_id = Column(Integer, nullable=True)
    chatwoot_inbox_id = Column(Integer, nullable=True)
    chatwoot_api_token = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
