from sqlalchemy import String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.models.external_base import ExternalBase

class Organization(ExternalBase):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True)
    trading_name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column()