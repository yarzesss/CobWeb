from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Watchlist(Base):
    __tablename__ = "watchlist"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    wallet_address: Mapped[str] = mapped_column(String(44), index=True)
    label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    added_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
