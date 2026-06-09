from sqlalchemy import String, DateTime, func, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum
from app.database import Base

class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    PREMIUM = "premium"

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    wallet_address: Mapped[str] = mapped_column(String(44), unique=True, index=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(SAEnum(SubscriptionTier), default=SubscriptionTier.FREE)
    last_seen: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
