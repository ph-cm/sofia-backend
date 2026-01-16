from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # quem é o profissional/tenant dono do evento
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    # dados do Google
    calendar_id: Mapped[str] = mapped_column(String(128), default="primary", nullable=False)
    event_id: Mapped[str] = mapped_column(String(256), index=True, nullable=False)

    start_datetime: Mapped[str] = mapped_column(String(64), nullable=False)
    end_datetime: Mapped[str] = mapped_column(String(64), nullable=False)

    summary: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    timezone: Mapped[str] = mapped_column(String(64), default="America/Sao_Paulo", nullable=False)

    # contexto (Chatwoot) - pode ser NULL
    conversation_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    contact_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    telefone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
