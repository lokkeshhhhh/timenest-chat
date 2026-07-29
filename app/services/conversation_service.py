from sqlalchemy import select
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_conversation import ChatConversation, ConversationType
from app.models.chat_participant import ChatParticipant
from app.models.user import User


class UserNotFoundError(Exception):
    pass


async def get_or_create_direct_conversation(
    db: AsyncSession,
    organization_id: int,
    current_user_id: int,
    participant_user_uuid: str,
) -> tuple[ChatConversation, bool]:
    """
    Returns (conversation, is_new).
    Pehle check karta hai ki dono users ke beech pehle se 'direct' conversation hai kya.
    Agar hai, wahi return karta hai. Agar nahi, naya banata hai.
    """
    # Step 1: participant ka internal user_id nikaalo uuid se
    result = await db.execute(select(User).where(User.uuid == participant_user_uuid))
    participant = result.scalar_one_or_none()
    if not participant:
        raise UserNotFoundError("Participant user not found")

    # Step 2: existing direct conversation dhoondo jisme YEH DONO users hain
    # Approach: Use table aliases to join ChatParticipant twice in a single query
    cp1 = aliased(ChatParticipant)
    cp2 = aliased(ChatParticipant)

    result = await db.execute(
        select(ChatConversation)
        .join(cp1, cp1.conversation_id == ChatConversation.id)
        .join(cp2, cp2.conversation_id == ChatConversation.id)
        .where(
            ChatConversation.type == ConversationType.DIRECT,
            ChatConversation.organization_id == organization_id,
            cp1.user_id == current_user_id,
            cp2.user_id == participant.id,
        )
    )
    existing_conv = result.scalar_one_or_none()
    
    if existing_conv:
        return existing_conv, False

    # Step 3: nahi mila, naya banao
    new_conversation = ChatConversation(
        organization_id=organization_id,
        type=ConversationType.DIRECT,
        created_by=current_user_id,
    )
    db.add(new_conversation)
    await db.flush()  # ID generate karwane ke liye, commit se pehle

    db.add(ChatParticipant(conversation_id=new_conversation.id, user_id=current_user_id))
    db.add(ChatParticipant(conversation_id=new_conversation.id, user_id=participant.id))

    await db.commit()
    await db.refresh(new_conversation)
    return new_conversation, True
