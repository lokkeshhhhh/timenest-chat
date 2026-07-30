"""Main entry for timenest-chat application.

Provides the FastAPI app and mounts routers for chat, health, and websocket.
"""

from fastapi import FastAPI
from app.websocket.routes import router as websocket_router
from app.api.conversation_routes import router as conversation_router
from app.core.config import get_settings
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="timenest-chat")
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(websocket_router)
app.include_router(conversation_router)


if __name__ == "__main__":
    # Lightweight dev server start when executed directly
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
