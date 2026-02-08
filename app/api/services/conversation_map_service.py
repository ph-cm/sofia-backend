from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.models.chatwoot_conversation_map import ChatwootConversationMap


class ConversationMapService:
    @staticmethod
    def upsert_map(
        db: Session,
        chatwoot_account_id: int,
        chatwoot_conversation_id: int,
        wa_phone_digits: str,
    ) -> ChatwootConversationMap:
        # normaliza
        wa_phone_digits = "".join(ch for ch in (wa_phone_digits or "") if ch.isdigit())

        stmt = select(ChatwootConversationMap).where(
            ChatwootConversationMap.chatwoot_account_id == chatwoot_account_id,
            ChatwootConversationMap.chatwoot_conversation_id == chatwoot_conversation_id,
        )
        row = db.execute(stmt).scalar_one_or_none()

        if row:
            row.wa_phone_digits = wa_phone_digits
            db.add(row)
            db.commit()
            db.refresh(row)
            return row

        row = ChatwootConversationMap(
            chatwoot_account_id=chatwoot_account_id,
            chatwoot_conversation_id=chatwoot_conversation_id,
            wa_phone_digits=wa_phone_digits,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def get_phone_by_conversation(
        db: Session,
        chatwoot_account_id: int,
        chatwoot_conversation_id: int,
    ) -> Optional[str]:
        stmt = select(ChatwootConversationMap.wa_phone_digits).where(
            ChatwootConversationMap.chatwoot_account_id == chatwoot_account_id,
            ChatwootConversationMap.chatwoot_conversation_id == chatwoot_conversation_id,
        )
        return db.execute(stmt).scalar_one_or_none()
