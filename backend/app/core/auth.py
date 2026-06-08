"""JWT helpers for Cobweb backend.

This module provides functions to create and verify JWT access tokens used
for authenticating protected endpoints. It uses python-jose for signing and
verification and reads secret and token lifetime from environment variables.

Functions:
- create_access_token
- decode_access_token
- verify_jwt_token
- get_current_user (FastAPI dependency returning TokenData)

Note: Database lookup for the user is left to the caller; this dependency
returns TokenData extracted from the token. Adjust SECRET/ALGORITHM via env.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

# Configuration (read from env; can be replaced by app.config later)
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-to-a-secure-secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRES_SECONDS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_SECONDS", "3600"))

security = HTTPBearer(auto_error=False)


class TokenData(BaseModel):
    wallet: str
    sub: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    extra: Dict[str, Any] = {}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(subject: str, wallet: str, expires_delta: Optional[timedelta] = None, **extra_claims: Any) -> str:
    """Create a signed JWT access token.

    Args:
        subject: Unique subject (e.g. user id)
        wallet: Wallet address string (solana pubkey)
        expires_delta: Optional timedelta to set expiry. Defaults to JWT_ACCESS_TOKEN_EXPIRES_SECONDS.
        extra_claims: Any additional claims to include in the token payload.

    Returns:
        Encoded JWT string.
    """
    now = _utc_now()
    if expires_delta is None:
        expires_delta = timedelta(seconds=JWT_ACCESS_TOKEN_EXPIRES_SECONDS)

    payload = {
        "sub": str(subject),
        "wallet": wallet,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    payload.update(extra_claims)

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_access_token(token: str) -> TokenData:
    """Decode and validate a JWT access token returning TokenData.

    Raises HTTPException(401) if invalid or expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Could not validate credentials") from exc

    if "wallet" not in payload:
        raise HTTPException(status_code=401, detail="Token missing wallet claim")

    return TokenData(
        wallet=payload.get("wallet"),
        sub=payload.get("sub"),
        exp=payload.get("exp"),
        iat=payload.get("iat"),
        extra={k: v for k, v in payload.items() if k not in {"wallet", "sub", "exp", "iat"}},
    )


def verify_jwt_token(token: str) -> bool:
    """Return True if token is valid (and not expired), False otherwise."""
    try:
        _ = decode_access_token(token)
        return True
    except HTTPException:
        return False


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> TokenData:
    """FastAPI dependency that extracts and verifies the JWT from Authorization header.

    Returns TokenData for use in route handlers. The actual user record lookup should
    be performed by the caller if needed (e.g., querying the database by wallet).
    """
    if credentials is None or not credentials.scheme or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = credentials.credentials
    token_data = decode_access_token(token)
    return token_data
