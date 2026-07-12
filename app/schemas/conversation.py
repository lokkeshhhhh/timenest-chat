from __future__ import annotations
from pydantic import BaseModel
from typing import List
from app.schemas.message import Message


class Conversation(BaseModel):
    id: str
    title: str
    messages: List[Message] = []
