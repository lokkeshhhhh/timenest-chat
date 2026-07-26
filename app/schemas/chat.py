from pydantic import BaseModel, Field

class IncomingMessage(BaseModel):
    conversation_uuid: str = Field(..., min_length=36, max_length=36)
    content: str = Field(..., min_length=1, max_length=5000)

class OutgoingMessage(BaseModel):
    conversation_uuid: str
    message_uuid: str
    content: str
    sender_uuid: str
    created_at: str