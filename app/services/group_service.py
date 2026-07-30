from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_conversation import ChatConversation, ConversationType
from app.models.chat_participant import ChatParticipant, ParticipantRole
from app.models.chat_message import ChatMessage, MessageType
from app.models.user import User


class NotAdminError(Exception):
    pass


class AlreadyParticipantError(Exception):
    pass


class NotParticipantError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


async def _get_user_by_uuid(db: AsyncSession, user_uuid: str) -> User:
    result = await db.execute(select(User).where(User.uuid == user_uuid))
    user = result.scalar_one_or_none()
    if not user:
        raise UserNotFoundError(f"User {user_uuid} not found")
    return user


async def _get_participant(db: AsyncSession, conversation_id: int, user_id: int) -> ChatParticipant | None:
    result = await db.execute(
        select(ChatParticipant).where(
            ChatParticipant.conversation_id == conversation_id,
            ChatParticipant.user_id == user_id,
            ChatParticipant.left_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def _create_system_message(db: AsyncSession, conversation_id: int, actor_id: int, content: str) -> ChatMessage:
    """Har group action (add/remove/leave) ke baad ek system message banta hai, jaisa 'X added Y'."""
    message = ChatMessage(
        conversation_id=conversation_id,
        sender_id=actor_id,
        content=content,
        message_type=MessageType.SYSTEM,
    )
    db.add(message)
    return message


async def create_group_conversation(
    db: AsyncSession,
    organization_id: int,
    creator_id: int,
    name: str,
    participant_user_uuids: list[str],
) -> ChatConversation:
    conversation = ChatConversation(
        organization_id=organization_id,
        type=ConversationType.GROUP,
        name=name,
        created_by=creator_id,
    )
    db.add(conversation)
    await db.flush()

    # Creator khud admin banega
    db.add(ChatParticipant(conversation_id=conversation.id, user_id=creator_id, role=ParticipantRole.ADMIN))

    for user_uuid in participant_user_uuids:
        user = await _get_user_by_uuid(db, user_uuid)
        db.add(ChatParticipant(conversation_id=conversation.id, user_id=user.id, role=ParticipantRole.MEMBER))

    await _create_system_message(db, conversation.id, creator_id, "Group created")

    await db.commit()
    await db.refresh(conversation)
    return conversation


async def add_participant(
    db: AsyncSession, conversation_id: int, actor_user_id: int, new_user_uuid: str
) -> tuple[ChatMessage, int]:
    """Returns (system_message, new_user_id) — taaki route broadcast kar sake."""
    actor_participant = await _get_participant(db, conversation_id, actor_user_id)
    if not actor_participant or actor_participant.role != ParticipantRole.ADMIN:
        raise NotAdminError("Only group admins can add members")

    new_user = await _get_user_by_uuid(db, new_user_uuid)

    existing = await _get_participant(db, conversation_id, new_user.id)
    if existing:
        raise AlreadyParticipantError("User is already a participant")

    db.add(ChatParticipant(conversation_id=conversation_id, user_id=new_user.id, role=ParticipantRole.MEMBER))

    result = await db.execute(select(User).where(User.id == actor_user_id))
    actor = result.scalar_one()
    system_msg = await _create_system_message(
        db, conversation_id, actor_user_id, f"{actor.name} added {new_user.name} to the group"
    )

    await db.commit()
    await db.refresh(system_msg)
    return system_msg, new_user.id


async def remove_participant(
    db: AsyncSession, conversation_id: int, actor_user_id: int, target_user_uuid: str
) -> ChatMessage:
    actor_participant = await _get_participant(db, conversation_id, actor_user_id)
    if not actor_participant or actor_participant.role != ParticipantRole.ADMIN:
        raise NotAdminError("Only group admins can remove members")

    target_user = await _get_user_by_uuid(db, target_user_uuid)
    target_participant = await _get_participant(db, conversation_id, target_user.id)
    if not target_participant:
        raise NotParticipantError("User is not a participant")

    target_participant.left_at = datetime.utcnow()

    result = await db.execute(select(User).where(User.id == actor_user_id))
    actor = result.scalar_one()
    system_msg = await _create_system_message(
        db, conversation_id, actor_user_id, f"{actor.name} removed {target_user.name} from the group"
    )

    await db.commit()
    await db.refresh(system_msg)
    return system_msg


async def leave_conversation(db: AsyncSession, conversation_id: int, user_id: int) -> ChatMessage:
    participant = await _get_participant(db, conversation_id, user_id)
    if not participant:
        raise NotParticipantError("You are not a participant of this group")

    participant.left_at = datetime.utcnow()

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    system_msg = await _create_system_message(db, conversation_id, user_id, f"{user.name} left the group")

    await db.commit()
    await db.refresh(system_msg)
    return system_msg
