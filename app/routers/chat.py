from fastapi import APIRouter
from app.schemas.conversation import Conversation
from app.services.chat_service import get_conversation

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/conversations", response_model=list[Conversation])
def list_conversations():
    """Return a list of active chat conversations."""
    return [get_conversation()]
