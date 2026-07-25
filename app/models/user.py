from sqlalchemy import String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.models.external_base import ExternalBase

class User(ExternalBase):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    token_version: Mapped[int] = mapped_column()