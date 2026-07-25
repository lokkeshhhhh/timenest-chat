import enum
import uuid as uuid_lib
from datetime import datetime
from sqlalchemy import String, BigInteger, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ConversationType(str, enum.Enum):
    DIRECT = "direct"
    GROUP = "group"


class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid_lib.uuid4()))
    organization_id: Mapped[int] = mapped_column(BigInteger, index=True)
    type: Mapped[ConversationType] = mapped_column(Enum(ConversationType))
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, index=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)