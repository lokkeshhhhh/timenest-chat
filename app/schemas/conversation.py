from __future__ import annotations
from pydantic import BaseModel
from typing import List
from app.schemas.message import Message


class Conversation(BaseModel):
    id: str
    title: str
    messages: List[Message] = []


class StartDirectConversationRequest(BaseModel):
    participant_user_uuid: str


class ConversationResponse(BaseModel):
    conversation_uuid: str
    type: str
    name: str | None
    is_new: bool
