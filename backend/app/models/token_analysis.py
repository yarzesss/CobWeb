from sqlalchemy import String, DateTime, Integer, Boolean, func, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column
import enum
from app.database import Base

class LifecycleStage(str, enum.Enum):
    ACCUMULATION = "accumulation"
    MARKUP = "markup"
    DISTRIBUTION = "distribution"
    DUMP = "dump"
    UNKNOWN = "unknown"

class TokenAnalysis(Base):
    __tablename__ = "token_analysis"
    id: Mapped[int] = mapped_column(primary_key=True)
    ca: Mapped[str] = mapped_column(String(44), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    dev_wallet: Mapped[str | None] = mapped_column(String(44), nullable=True)
    dev_risk_score: Mapped[int] = mapped_column(Integer, default=0)
    dev_prev_tokens: Mapped[int] = mapped_column(Integer, default=0)
    dev_rug_count: Mapped[int] = mapped_column(Integer, default=0)
    lifecycle_stage: Mapped[LifecycleStage] = mapped_column(SAEnum(LifecycleStage), default=LifecycleStage.UNKNOWN)
    is_bundled: Mapped[bool] = mapped_column(Boolean, default=False)
    sniper_count: Mapped[int] = mapped_column(Integer, default=0)
    early_buyers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cabal_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    total_early_buyers: Mapped[int] = mapped_column(Integer, default=0)
    analyzed_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
