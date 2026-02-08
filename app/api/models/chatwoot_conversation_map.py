from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime, func, UniqueConstraint, Index
from app.db.base_class import Base  # ajuste se seu Base estiver em outro path


class ChatwootConversationMap(Base):
    __tablename__ = "chatwoot_conversation_map"

    id = Column(Integer, primary_key=True, index=True)

    chatwoot_account_id = Column(Integer, nullable=False, index=True)
    chatwoot_conversation_id = Column(Integer, nullable=False, index=True)

    # telefone do paciente (somente dígitos) ex: 5534999999999
    wa_phone_digits = Column(String(32), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("chatwoot_account_id", "chatwoot_conversation_id", name="uq_cw_account_conversation"),
        Index("ix_cw_map_account_phone", "chatwoot_account_id", "wa_phone_digits"),
    )
