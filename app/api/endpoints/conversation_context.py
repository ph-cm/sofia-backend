from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.services.conversation_context_service import (
    get_by_conversation_id,
    upsert_context,
)
from app.schemas.conversation_context import (
    ConversationContextCreate,
    ConversationContextResponse,
)

router = APIRouter(prefix="/conversation-context", tags=["Conversation Context"])

@router.get("/{conversation_id}", response_model=ConversationContextResponse)
def get_context(conversation_id: str, db: Session = Depends(get_db)):
    context = get_by_conversation_id(db, conversation_id)
    if not context:
        raise HTTPException(status_code=404, detail="Context not set")
    return context

@router.post("", response_model=ConversationContextResponse)
def save_context(
    payload: ConversationContextCreate,
    db: Session = Depends(get_db),
):
    return upsert_context(
        db,
        payload.conversation_id,
        payload.user_id,
    )
