from pydantic import BaseModel

class ConversationContextCreate(BaseModel):
    conversation_id: str
    user_id: str

class ConversationContextResponse(BaseModel):
    conversation_id: str
    user_id: str
