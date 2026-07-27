import uuid as uuid_lib
from datetime import datetime
from sqlalchemy import BigInteger, String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ChatAttachment(Base):
    __tablename__ = "chat_attachments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid_lib.uuid4()))
    message_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chat_messages.id"))
    file_url: Mapped[str] = mapped_column(String(1000))
    file_type: Mapped[str] = mapped_column(String(50))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size_bytes: Mapped[int] = mapped_column(BigInteger)
    original_filename: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
