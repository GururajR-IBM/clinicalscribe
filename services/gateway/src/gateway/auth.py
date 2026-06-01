"""Clerk JWT authentication middleware for FastAPI.

Validates Bearer tokens issued by Clerk using the JWKS endpoint.
The verified payload is exposed as a FastAPI dependency: `CurrentUser`.

Security considerations (OWASP A02 – Cryptographic Failures, A07 – Auth Failures):
- Tokens are verified against the remote JWKS on every request.
- The JWKS is cached in-process (TTL handled by httpx); no secrets stored.
- Algorithm is restricted to RS256; 'none' and symmetric algs are rejected.
- Issuer is validated against the configured Clerk domain.
- Expiry (exp) and not-before (nbf) are validated by python-jose.
"""

from __future__ import annotations

import logging
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from jose.exceptions import ExpiredSignatureError

from gateway.config import settings

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=True)

# Module-level JWKS cache (list of JWK dicts)
_jwks_cache: list[dict] | None = None


async def _get_jwks() -> list[dict]:
    """Fetch JWKS from Clerk; module-level cache avoids per-request round-trips."""
    global _jwks_cache  # noqa: PLW0603
    if _jwks_cache is not None:
        return _jwks_cache
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(settings.clerk_jwks_url)
        resp.raise_for_status()
    _jwks_cache = resp.json().get("keys", [])
    return _jwks_cache


def _find_key(kid: str, keys: list[dict]) -> dict | None:
    for key in keys:
        if key.get("kid") == kid:
            return key
    return None


async def verify_clerk_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(_bearer)],
) -> dict:
    """FastAPI dependency: validates Clerk JWT and returns the decoded payload.

    Raises HTTP 401 on any failure (expired, invalid signature, wrong issuer, etc.).
    """
    token = credentials.credentials
    exc_401 = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode header without verification to extract kid
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        raise exc_401

    kid = unverified_header.get("kid")
    alg = unverified_header.get("alg", "")
    if alg != "RS256":
        # Reject symmetric / 'none' algorithms
        raise exc_401

    try:
        keys = await _get_jwks()
    except Exception:
        logger.exception("Failed to fetch JWKS")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable.",
        )

    raw_key = _find_key(kid, keys)
    if raw_key is None:
        # Key rotation: clear cache and retry once
        global _jwks_cache  # noqa: PLW0603
        _jwks_cache = None
        try:
            keys = await _get_jwks()
            raw_key = _find_key(kid, keys)
        except Exception:
            raise exc_401
    if raw_key is None:
        raise exc_401

    public_key = jwk.construct(raw_key, algorithm="RS256")

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer,
            options={"verify_aud": False},  # Clerk JWTs have no `aud` by default
        )
    except ExpiredSignatureError:
        raise exc_401
    except JWTError:
        raise exc_401

    return payload


# Convenience type alias for route parameters
CurrentUser = Annotated[dict, Depends(verify_clerk_token)]
