"""Auth router — Web3 wallet signature verification."""
from __future__ import annotations

import secrets
from typing import Any

import base58
from fastapi import APIRouter, HTTPException
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from pydantic import BaseModel

from app.config import settings
from app.core.auth import create_access_token
from app.core.cache import delete_key, get_json, set_json

router = APIRouter(prefix="/auth", tags=["Auth"])

NONCE_TTL = 300  # 5 хвилин


class NonceResponse(BaseModel):
    wallet: str
    nonce: str
    expires_in: int


class VerifyRequest(BaseModel):
    wallet: str
    signature: str
    nonce: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.get("/nonce", response_model=NonceResponse)
async def get_nonce(wallet: str) -> Any:
    """Generate a one-time nonce for wallet signature verification."""
    if not wallet:
        raise HTTPException(status_code=400, detail="wallet query param required")

    nonce = secrets.token_urlsafe(24)
    await set_json(f"auth:nonce:{wallet}", nonce, ttl=NONCE_TTL)

    return NonceResponse(wallet=wallet, nonce=nonce, expires_in=NONCE_TTL)


@router.post("/verify", response_model=TokenResponse)
async def verify_signature(payload: VerifyRequest) -> Any:
    """
    Verify wallet signature and return JWT.

    Frontend must sign exactly: f"Sign in to Cobweb: {nonce}"
    """
    cache_key = f"auth:nonce:{payload.wallet}"
    stored_nonce = await get_json(cache_key)

    if stored_nonce is None or stored_nonce != payload.nonce:
        raise HTTPException(status_code=400, detail="Invalid or expired nonce")

    message = f"Sign in to Cobweb: {payload.nonce}".encode("utf-8")

    try:
        pubkey_bytes = base58.b58decode(payload.wallet)
        sig_bytes = base58.b58decode(payload.signature)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base58 encoding")

    try:
        VerifyKey(pubkey_bytes).verify(message, sig_bytes)
    except BadSignatureError:
        raise HTTPException(status_code=401, detail="Signature verification failed")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Verification error: {exc}")

    # Nonce одноразовий — видаляємо після успішної верифікації
    await delete_key(cache_key)

    token = create_access_token(wallet=payload.wallet)
    return TokenResponse(access_token=token)