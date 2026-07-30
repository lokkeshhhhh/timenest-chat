from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import ValidationError

from app.core.database import AsyncSessionLocal
from app.auth.dependencies import get_current_user
from app.websocket.connection_manager import manager
from app.schemas.chat import IncomingMessage, OutgoingMessage, MarkAsReadEvent
from app.services.chat_service import (
    verify_participant_and_get_conversation,
    save_message,
    get_other_participant_uuids,
    mark_conversation_read,
    MembershipError,
    ConversationNotFoundError,
)

router = APIRouter()


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket, token: str = Query(...)):
    async with AsyncSessionLocal() as db:
        try:
            auth_context = await get_current_user(token=token, db=db)
        except Exception as e:
            print(f"WebSocket Auth Failed: {e}")
            await websocket.close(code=4401)
            return

    await websocket.accept()
    await manager.connect(auth_context.user_uuid, websocket)

    try:
        while True:
            raw_data = await websocket.receive_json()
            event_type = raw_data.get("type", "message")

            if event_type == "mark_as_read":
                await handle_mark_as_read(websocket, raw_data, auth_context)
            else:
                await handle_send_message(websocket, raw_data, auth_context)

    except WebSocketDisconnect:
        manager.disconnect(auth_context.user_uuid, websocket)


async def handle_send_message(websocket: WebSocket, raw_data: dict, auth_context):
    try:
        incoming = IncomingMessage(**raw_data)
    except ValidationError as e:
        await websocket.send_json({"error": "Invalid message format", "details": e.errors()})
        return

    async with AsyncSessionLocal() as db:
        try:
            conversation = await verify_participant_and_get_conversation(
                db, incoming.conversation_uuid, auth_context.user_id
            )
        except ConversationNotFoundError:
            await websocket.send_json({"error": "Conversation not found"})
            return
        except MembershipError:
            await websocket.send_json({"error": "You are not part of this conversation"})
            return

        message = await save_message(db, conversation, auth_context.user_id, incoming.content)
        other_user_uuids = await get_other_participant_uuids(db, conversation.id, auth_context.user_uuid)

    outgoing = OutgoingMessage(
        message_uuid=message.uuid,
        conversation_uuid=incoming.conversation_uuid,
        sender_uuid=auth_context.user_uuid,
        content=message.content,
        created_at=message.created_at.isoformat(),
    )
    await manager.broadcast_to_users(other_user_uuids, outgoing.model_dump())
    await websocket.send_json({"status": "sent", "message": outgoing.model_dump()})


async def handle_mark_as_read(websocket: WebSocket, raw_data: dict, auth_context):
    try:
        event = MarkAsReadEvent(**raw_data)
    except ValidationError as e:
        await websocket.send_json({"error": "Invalid mark_as_read format", "details": e.errors()})
        return

    async with AsyncSessionLocal() as db:
        try:
            conversation = await verify_participant_and_get_conversation(
                db, event.conversation_uuid, auth_context.user_id
            )
        except (ConversationNotFoundError, MembershipError):
            await websocket.send_json({"error": "Cannot mark as read"})
            return

        read_at = await mark_conversation_read(db, conversation.id, auth_context.user_id)
        other_user_uuids = await get_other_participant_uuids(db, conversation.id, auth_context.user_uuid)

    # Baaki participants ko batao "yeh user ne padh liya"
    await manager.broadcast_to_users(other_user_uuids, {
        "type": "read_receipt",
        "conversation_uuid": event.conversation_uuid,
        "reader_uuid": auth_context.user_uuid,
        "read_at": read_at.isoformat(),
    })