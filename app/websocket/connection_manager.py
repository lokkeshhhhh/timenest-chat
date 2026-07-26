from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, user_uuid: str, websocket: WebSocket):
        if user_uuid not in self.active_connections:
            self.active_connections[user_uuid] = []
        self.active_connections[user_uuid].append(websocket)

    def disconnect(self, user_uuid: str, websocket: WebSocket):
        if user_uuid in self.active_connections:
            self.active_connections[user_uuid].remove(websocket)
            if not self.active_connections[user_uuid]:
                del self.active_connections[user_uuid]

    async def send_to_user(self, user_uuid: str, message: dict):
        if user_uuid in self.active_connections:
            for conn in self.active_connections[user_uuid]:
                await conn.send_json(message)

    async def broadcast_to_users(self, user_uuids: list[str], message: dict):
        for user_uuid in user_uuids:
            await self.send_to_user(user_uuid, message)


manager = ConnectionManager()