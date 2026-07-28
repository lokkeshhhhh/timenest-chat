from sqlalchemy import select
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
    # Approach: un conversations ko dhoondo jinme current_user hai, type='direct',
    # phir un me se check karo kis me participant bhi hai
    result = await db.execute(
        select(ChatConversation)
        .join(ChatParticipant, ChatParticipant.conversation_id == ChatConversation.id)
        .where(
            ChatConversation.type == ConversationType.DIRECT,
            ChatConversation.organization_id == organization_id,
            ChatParticipant.user_id == current_user_id,
        )
    )
    candidate_conversations = result.scalars().all()

    for conv in candidate_conversations:
        result = await db.execute(
            select(ChatParticipant).where(
                ChatParticipant.conversation_id == conv.id,
                ChatParticipant.user_id == participant.id,
            )
        )
        if result.scalar_one_or_none():
            return conv, False  # existing conversation mil gaya

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
