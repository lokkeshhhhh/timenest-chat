from datetime import datetime
import enum
from sqlalchemy import BigInteger, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ParticipantRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"


class ChatParticipant(Base):
    __tablename__ = "chat_participants"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chat_conversations.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    role: Mapped[ParticipantRole] = mapped_column(Enum(ParticipantRole), default=ParticipantRole.MEMBER)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    left_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)