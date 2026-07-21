from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["health"])


class PingResponse(BaseModel):
    status: str
    message: Optional[str] = None


@router.get("/", response_model=PingResponse)
def root():
    """Root health endpoint."""
    return {"status": "ok", "message": "timenest-chat running"}


@router.get("/ping", response_model=PingResponse)
def ping():
    """Simple ping endpoint."""
    return {"status": "ok", "message": "pong"}


@router.get("/lokeshji", response_model=PingResponse)
def lokeshji():
    return {"status": "failed"}