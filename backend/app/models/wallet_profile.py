from sqlalchemy import String, DateTime, Float, Integer, func, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum
from app.database import Base

class WalletArchetype(str, enum.Enum):
    SNIPER = "sniper"
    INSIDER = "insider"
    SWING_TRADER = "swing"
    ACCUMULATOR = "accumulator"
    FLIPPER = "flipper"
    BOT = "bot"
    UNKNOWN = "unknown"

class WalletProfile(Base):
    __tablename__ = "wallet_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    wallet_address: Mapped[str] = mapped_column(String(44), unique=True, index=True)
    archetype: Mapped[WalletArchetype] = mapped_column(SAEnum(WalletArchetype), default=WalletArchetype.UNKNOWN)
    bot_score: Mapped[int] = mapped_column(Integer, default=0)
    smart_money_score: Mapped[int] = mapped_column(Integer, default=0)
    winrate: Mapped[float] = mapped_column(Float, default=0.0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    total_pnl_usd: Mapped[float] = mapped_column(Float, default=0.0)
    avg_position_size_usd: Mapped[float] = mapped_column(Float, default=0.0)
    avg_hold_time_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    favorite_dex: Mapped[str | None] = mapped_column(String(50), nullable=True)
    first_seen: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    last_active: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
