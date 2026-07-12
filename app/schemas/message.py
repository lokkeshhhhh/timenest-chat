from pydantic import BaseModel


class Message(BaseModel):
    id: str
    sender: str
    content: str
    timestamp: str
