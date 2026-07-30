from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.auth.dependencies import get_current_user_from_header, AuthContext
from app.schemas.conversation import StartDirectConversationRequest, ConversationResponse, ConversationListItem, MessageHistoryResponse, MessageHistoryItem
from app.services.conversation_service import get_or_create_direct_conversation, UserNotFoundError, get_user_conversations, get_conversation_messages
from app.models.user import User
from app.models.chat_conversation import ChatConversation

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("/direct", response_model=ConversationResponse)
async def start_direct_conversation(
    payload: StartDirectConversationRequest,
    auth: AuthContext = Depends(get_current_user_from_header),
    db: AsyncSession = Depends(get_db),
):
    # organization_id internal id chahiye (auth me organization_uuid hai)
    from app.models.organization import Organization
    result = await db.execute(select(Organization).where(Organization.uuid == auth.organization_uuid))
    organization = result.scalar_one_or_none()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    try:
        conversation, is_new = await get_or_create_direct_conversation(
            db, organization.id, auth.user_id, payload.participant_user_uuid
        )
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="Participant user not found")

    return ConversationResponse(
        conversation_uuid=conversation.uuid,
        type=conversation.type.value,
        name=conversation.name,
        is_new=is_new,
    )


@router.get("", response_model=list[ConversationListItem])
async def list_conversations(
    auth: AuthContext = Depends(get_current_user_from_header),
    db: AsyncSession = Depends(get_db),
):
    conversations = await get_user_conversations(db, auth.user_id)
    return [
        ConversationListItem(
            conversation_uuid=c.uuid,
            type=c.type.value,
            name=c.name,
            avatar_url=c.avatar_url,
            last_message_at=c.last_message_at,
        )
        for c in conversations
    ]


@router.get("/{conversation_uuid}/messages", response_model=MessageHistoryResponse)
async def get_messages(
    conversation_uuid: str,
    before: str | None = Query(default=None, description="message_uuid for pagination cursor"),
    limit: int = Query(default=20, le=100),
    auth: AuthContext = Depends(get_current_user_from_header),
    db: AsyncSession = Depends(get_db),
):
    # Membership verify (reuse Step 9 ka function)
    from app.services.chat_service import verify_participant_and_get_conversation, MembershipError, ConversationNotFoundError

    try:
        conversation = await verify_participant_and_get_conversation(db, conversation_uuid, auth.user_id)
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except MembershipError:
        raise HTTPException(status_code=403, detail="Not a participant")

    messages, has_more = await get_conversation_messages(db, conversation.id, limit=limit, before_message_uuid=before)

    # sender_id -> sender_uuid map banane ke liye ek quick lookup
    sender_ids = {m.sender_id for m in messages}
    result = await db.execute(select(User).where(User.id.in_(sender_ids)))
    users_map = {u.id: u.uuid for u in result.scalars().all()}

    items = [
        MessageHistoryItem(
            message_uuid=m.uuid,
            sender_uuid=users_map.get(m.sender_id, ""),
            content=m.content,
            message_type=m.message_type.value,
            created_at=m.created_at,
        )
        for m in messages
    ]

    return MessageHistoryResponse(
        messages=items,
        has_more=has_more,
        next_cursor=items[0].message_uuid if items and has_more else None,
    )
