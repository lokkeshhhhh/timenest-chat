from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime
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


class ConversationListItem(BaseModel):
    conversation_uuid: str
    type: str
    name: str | None
    avatar_url: str | None
    last_message_at: datetime | None
    unread_count: int = 0


class MessageHistoryItem(BaseModel):
    message_uuid: str
    sender_uuid: str
    content: str
    message_type: str
    created_at: datetime


class MessageHistoryResponse(BaseModel):
    messages: list[MessageHistoryItem]
    has_more: bool
    next_cursor: str | None


class CreateGroupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    participant_user_uuids: list[str] = Field(..., min_length=1)


class AddParticipantRequest(BaseModel):
    user_uuid: str


class GroupActionResponse(BaseModel):
    success: bool
    message: str
