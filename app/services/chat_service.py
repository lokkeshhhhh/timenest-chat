from app.schemas.conversation import Conversation
from app.schemas.message import Message


def get_conversation() -> Conversation:
    return Conversation(
        id="conversation-1",
        title="General Chat",
        messages=[
            Message(
                id="message-1",
                sender="system",
                content="Welcome to timenest-chat!",
                timestamp="2026-07-12T00:00:00Z",
            )
        ],
    )
