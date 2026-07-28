from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.auth.dependencies import get_current_user_from_header, AuthContext
from app.schemas.conversation import StartDirectConversationRequest, ConversationResponse
from app.services.conversation_service import get_or_create_direct_conversation, UserNotFoundError
from app.models.user import User

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
