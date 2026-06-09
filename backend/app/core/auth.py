"""JWT helpers for Cobweb backend."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import settings

security = HTTPBearer(auto_error=False)


class TokenData(BaseModel):
    wallet: str
    sub: Optional[str] = None
    exp: Optional[int] = None


def create_access_token(wallet: str) -> str:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    payload = {
        "sub": wallet,
        "wallet": wallet,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    wallet = payload.get("wallet")
    if not wallet:
        raise HTTPException(status_code=401, detail="Token missing wallet claim")

    return TokenData(
        wallet=wallet,
        sub=payload.get("sub"),
        exp=payload.get("exp"),
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> TokenData:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return decode_access_token(credentials.credentials)