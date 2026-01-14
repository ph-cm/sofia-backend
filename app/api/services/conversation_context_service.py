from sqlalchemy.orm import Session
from app.api.models.conversation_context import ConversationContext

def get_by_conversation_id(db: Session, conversation_id: str):
    return (
        db.query(ConversationContext)
        .filter(ConversationContext.conversation_id == conversation_id)
        .first()
    )

def upsert_context(db: Session, conversation_id: str, user_id: str):
    context = get_by_conversation_id(db, conversation_id)

    if context:
        context.user_id = user_id
    else:
        context = ConversationContext(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        db.add(context)

    db.commit()
    db.refresh(context)
    return context
