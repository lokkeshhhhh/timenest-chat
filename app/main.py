"""Main entry for timenest-chat application.

Provides the FastAPI app and mounts routers for chat, health, and websocket.
"""

from fastapi import FastAPI
from app.routers.chat import router as chat_router
from app.routers.health import router as health_router
from app.websocket.routes import router as websocket_router

app = FastAPI(title="timenest-chat")

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(websocket_router)


if __name__ == "__main__":
    # Lightweight dev server start when executed directly
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
