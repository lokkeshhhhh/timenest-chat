from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import ValidationError

from app.core.database import AsyncSessionLocal
from app.auth.dependencies import get_current_user
from app.websocket.connection_manager import manager
from app.schemas.chat import IncomingMessage, OutgoingMessage
from app.services.chat_service import (
    verify_participant_and_get_conversation,
    save_message,
    get_other_participant_uuids,
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

    # Auth pass ho gaya — ab connection accept karo
    await websocket.accept()
    # Yaha `user_uuid` use kiya hai kyunki ConnectionManager ab UUIDs pe chalta hai!
    await manager.connect(auth_context.user_uuid, websocket)

    try:
        while True:
            raw_data = await websocket.receive_json()

            # Step 1: Validate incoming shape
            try:
                incoming = IncomingMessage(**raw_data)
            except ValidationError as e:
                await websocket.send_json({"error": "Invalid message format", "details": e.errors()})
                continue

            async with AsyncSessionLocal() as db:
                # Step 2: Membership verify (Yeh fast hai kyunki ye internal auth_context.user_id leta hai)
                try:
                    conversation = await verify_participant_and_get_conversation(
                        db, incoming.conversation_uuid, auth_context.user_id
                    )
                except ConversationNotFoundError:
                    await websocket.send_json({"error": "Conversation not found"})
                    continue
                except MembershipError:
                    await websocket.send_json({"error": "You are not part of this conversation"})
                    continue

                # Step 3 + 4: Save message, update last_message_at
                message = await save_message(db, conversation, auth_context.user_id, incoming.content)

                # Step 5: Other participants nikaalo (Yeh UUIDs return karega manager ke liye)
                other_uuids = await get_other_participant_uuids(db, conversation.id, auth_context.user_uuid)

            # Step 6: Broadcast (live connected users ko)
            outgoing = OutgoingMessage(
                message_uuid=message.uuid,
                conversation_uuid=incoming.conversation_uuid,
                sender_uuid=auth_context.user_uuid,  # Frontend ke liye uuid
                content=message.content,
                created_at=message.created_at.isoformat(),
            )
            
            # Broadcast karo (UUID list ke zariye)
            await manager.broadcast_to_users(other_uuids, outgoing.model_dump())

            # Sender ko bhi confirmation bhejna acha UX hai (uska apna message turant dikhe)
            await websocket.send_json({"status": "sent", "message": outgoing.model_dump()})

    except WebSocketDisconnect:
        # Disconnect bhi uuid ke through
        manager.disconnect(auth_context.user_uuid, websocket)