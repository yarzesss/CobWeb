from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "SolanaIntel"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database (поки що не використовується роутерами — watchlist живе в Redis)
    DATABASE_URL: str = "postgresql+asyncpg://cobweb:cobweb@postgres:5432/cobweb"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Helius RPC
    HELIUS_API_KEY: str
    HELIUS_RPC_URL: str = "https://mainnet.helius-rpc.com"
    HELIUS_API_URL: str = "https://api.helius.xyz/v0"

    # Auth
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 днів

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""

    # Cache TTL (секунди)
    CACHE_TTL_TOKEN: int = 300       # 5 хвилин — дані токена
    CACHE_TTL_WALLET: int = 600      # 10 хвилин — профіль гаманця
    CACHE_TTL_CABAL: int = 1800      # 30 хвилин — cabal аналіз

    # Rate limiting
    HELIUS_REQUESTS_PER_SECOND: int = 10
    MAX_WALLETS_PER_CABAL_SCAN: int = 50  # скільки гаманців аналізуємо за раз

    # Early buyers
    EARLY_BUY_MARKET_CAP_USD: int = 10000  # поріг "ранній покупець" — 10k капа
    MAX_TX_PAGES_FOR_EARLY_BUYERS: int = 30  # макс. сторінок історії (30 × 100 = 3000 tx)
    MAX_EARLY_BUYERS: int = 150  # скільки перших унікальних покупців вважаємо "ранніми"

    # Prices
    CACHE_TTL_PRICE: int = 60                # 1 хвилина — ціна SOL
    SOL_PRICE_FALLBACK_USD: float = 150.0    # якщо всі price API недоступні

    # CORS
    FRONTEND_ORIGIN: str = "https://cobweb.so"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()