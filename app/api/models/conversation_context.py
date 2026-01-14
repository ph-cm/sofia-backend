from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base_class import Base

class ConversationContext(Base):
    __tablename__ = "conversation_context"

    conversation_id = Column(String, primary_key=True, index=True)
    user_id = Column(int, nullable=False)
    tenant_id = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
