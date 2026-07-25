import enum
import uuid as uuid_lib
from datetime import datetime
from sqlalchemy import String, BigInteger, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class MessageType(str, enum.Enum):
    TEXT = "text"
    SYSTEM = "system"

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid_lib.uuid4()))
    conversation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chat_conversations.id"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    message_type: Mapped[MessageType] = mapped_column(Enum(MessageType), default=MessageType.TEXT)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)