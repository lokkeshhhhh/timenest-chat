from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_conversation import ChatConversation
from app.models.chat_participant import ChatParticipant
from app.models.chat_message import ChatMessage, MessageType
from app.models.user import User


class MembershipError(Exception):
    """Jab sender us conversation ka participant nahi hai."""
    pass


class ConversationNotFoundError(Exception):
    pass


async def verify_participant_and_get_conversation(
    db: AsyncSession, conversation_uuid: str, user_id: int
) -> ChatConversation:
    """
    Step 2: Membership check.
    Confirm karta hai ki (a) conversation exist karta hai, (b) yeh user uska participant hai.
    """
    result = await db.execute(
        select(ChatConversation).where(ChatConversation.uuid == conversation_uuid)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise ConversationNotFoundError("Conversation not found")

    result = await db.execute(
        select(ChatParticipant).where(
            ChatParticipant.conversation_id == conversation.id,
            ChatParticipant.user_id == user_id,
            ChatParticipant.left_at.is_(None),
        )
    )
    participant = result.scalar_one_or_none()
    if not participant:
        raise MembershipError("You are not a participant of this conversation")

    return conversation


async def save_message(
    db: AsyncSession, conversation: ChatConversation, sender_id: int, content: str
) -> ChatMessage:
    """Step 3 + 4: Message save karo, conversation ka last_message_at update karo."""
    message = ChatMessage(
        conversation_id=conversation.id,
        sender_id=sender_id,
        content=content,
        message_type=MessageType.TEXT,
    )
    db.add(message)

    conversation.last_message_at = datetime.utcnow()

    await db.commit()
    await db.refresh(message)
    return message


async def get_other_participant_uuids(
    db: AsyncSession, conversation_id: int, exclude_user_uuid: str
) -> list[str]:
    """Step 5: Broadcast ke liye — sab participants nikaalo (unke UUIDs), sender ko chhod ke."""
    result = await db.execute(
        select(User.uuid)
        .join(ChatParticipant, ChatParticipant.user_id == User.id)
        .where(
            ChatParticipant.conversation_id == conversation_id,
            ChatParticipant.left_at.is_(None),
            User.uuid != exclude_user_uuid,
        )
    )
    return [row[0] for row in result.all()]