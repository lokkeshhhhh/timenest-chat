from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.auth.dependencies import get_current_user_from_header, AuthContext
from app.schemas.conversation import (
    StartDirectConversationRequest, ConversationResponse, ConversationListItem, 
    MessageHistoryResponse, MessageHistoryItem, CreateGroupRequest, AddParticipantRequest, GroupActionResponse
)
from app.services.conversation_service import (
    get_or_create_direct_conversation, UserNotFoundError, get_user_conversations, get_conversation_messages, get_conversation_by_uuid
)
from app.services.group_service import (
    create_group_conversation, add_participant, remove_participant, leave_conversation,
    NotAdminError, AlreadyParticipantError, NotParticipantError, UserNotFoundError as GroupUserNotFoundError
)
from app.services.chat_service import get_other_participant_uuids
from app.models.user import User
from app.models.chat_conversation import ChatConversation
from app.models.organization import Organization
from app.websocket.connection_manager import manager

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("/direct", response_model=ConversationResponse)
async def start_direct_conversation(
    payload: StartDirectConversationRequest,
    auth: AuthContext = Depends(get_current_user_from_header),
    db: AsyncSession = Depends(get_db),
):
    # organization_id internal id chahiye (auth me organization_uuid hai)
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
    conversations_with_counts = await get_user_conversations(db, auth.user_id)
    return [
        ConversationListItem(
            conversation_uuid=c.uuid,
            type=c.type.value,
            name=c.name,
            avatar_url=c.avatar_url,
            last_message_at=c.last_message_at,
            unread_count=unread_count,
        )
        for c, unread_count in conversations_with_counts
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


@router.post("/group", response_model=ConversationResponse)
async def create_group(
    payload: CreateGroupRequest,
    auth: AuthContext = Depends(get_current_user_from_header),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Organization).where(Organization.uuid == auth.organization_uuid))
    organization = result.scalar_one_or_none()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    try:
        conversation = await create_group_conversation(
            db, organization.id, auth.user_id, payload.name, payload.participant_user_uuids
        )
    except GroupUserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return ConversationResponse(
        conversation_uuid=conversation.uuid,
        type=conversation.type.value,
        name=conversation.name,
        is_new=True,
    )


@router.post("/{conversation_uuid}/participants", response_model=GroupActionResponse)
async def add_group_participant(
    conversation_uuid: str,
    payload: AddParticipantRequest,
    auth: AuthContext = Depends(get_current_user_from_header),
    db: AsyncSession = Depends(get_db),
):
    conversation = await get_conversation_by_uuid(db, conversation_uuid)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        system_msg, new_user_id = await add_participant(db, conversation.id, auth.user_id, payload.user_uuid)
    except NotAdminError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except AlreadyParticipantError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GroupUserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Naya member add hone par group ke baaki members ko websocket alert bhejte hain
    participant_uuids = await get_other_participant_uuids(db, conversation.id, exclude_user_uuid="")
    await manager.broadcast_to_users(
        participant_uuids,
        {
            "event": "member_added",
            "conversation_uuid": conversation.uuid,
            "system_message": system_msg.content,
        }
    )

    return GroupActionResponse(success=True, message="Participant added successfully")


@router.delete("/{conversation_uuid}/participants/{user_uuid}", response_model=GroupActionResponse)
async def remove_group_participant(
    conversation_uuid: str,
    user_uuid: str,
    auth: AuthContext = Depends(get_current_user_from_header),
    db: AsyncSession = Depends(get_db),
):
    conversation = await get_conversation_by_uuid(db, conversation_uuid)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        system_msg = await remove_participant(db, conversation.id, auth.user_id, user_uuid)
    except NotAdminError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotParticipantError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GroupUserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    participant_uuids = await get_other_participant_uuids(db, conversation.id, exclude_user_uuid="")
    await manager.broadcast_to_users(
        participant_uuids,
        {
            "event": "member_removed",
            "conversation_uuid": conversation.uuid,
            "system_message": system_msg.content,
        }
    )

    return GroupActionResponse(success=True, message="Participant removed successfully")


@router.post("/{conversation_uuid}/leave", response_model=GroupActionResponse)
async def leave_group_conversation(
    conversation_uuid: str,
    auth: AuthContext = Depends(get_current_user_from_header),
    db: AsyncSession = Depends(get_db),
):
    conversation = await get_conversation_by_uuid(db, conversation_uuid)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        system_msg = await leave_conversation(db, conversation.id, auth.user_id)
    except NotParticipantError as e:
        raise HTTPException(status_code=400, detail=str(e))

    participant_uuids = await get_other_participant_uuids(db, conversation.id, exclude_user_uuid="")
    await manager.broadcast_to_users(
        participant_uuids,
        {
            "event": "member_left",
            "conversation_uuid": conversation.uuid,
            "system_message": system_msg.content,
        }
    )

    return GroupActionResponse(success=True, message="Left group successfully")
