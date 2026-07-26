from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.auth.dependencies import get_current_user
from app.auth.jwt_handler import InvalidTokenError
from app.websocket.connection_manager import manager

router = APIRouter()


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket, token: str = Query(...)):
    # WebSocket me Depends() seedha kaam nahi karta jaisa REST routes me karta hai,
    # isliye humein manually session banake, manually get_current_user call karna padega.
    async with AsyncSessionLocal() as db:
        try:
            auth_context = await get_current_user(token=token, db=db)
        except Exception:
            # Connection accept karne se PEHLE reject — client ko clean error milega
            await websocket.close(code=4401)  # custom code: unauthorized
            return

    # Auth pass ho gaya — ab connection accept karo
    await websocket.accept()
    await manager.connect(auth_context.user_id, websocket)

    try:
        while True:
            # Client se message wait karo (yeh line block karti hai jab tak naya message na aaye)
            data = await websocket.receive_json()
            # Abhi ke liye sirf echo kar rahe hain — Step 9 me actual save-to-DB + broadcast aayega
            await websocket.send_json({"echo": data, "from_user": auth_context.user_id})

    except WebSocketDisconnect:
        manager.disconnect(auth_context.user_id, websocket)