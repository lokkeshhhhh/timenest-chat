from fastapi import APIRouter
from app.schemas.conversation import Conversation

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/conversations", response_model=list[Conversation])
def list_conversations():
    """Return a list of active chat conversations."""
    return []
