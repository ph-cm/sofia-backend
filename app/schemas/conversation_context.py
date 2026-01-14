from pydantic import BaseModel

class ConversationContextCreate(BaseModel):
    conversation_id: str
    user_id: int

class ConversationContextResponse(BaseModel):
    conversation_id: str
    user_id: int
