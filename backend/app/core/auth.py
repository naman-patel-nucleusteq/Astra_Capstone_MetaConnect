"""
Keycloak JWT authentication for MetaConnect FastAPI.
"""

import time
import logging
from typing import Any
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from app.core.config import KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID


log = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=True)
bearer_scheme_optional = HTTPBearer(auto_error=False)


# JWKS cache
jwks_cache: dict[str, Any] = {}
jwks_fetched_at: float = 0.0
JWKS_TTL = 300  


def jwks_uri() -> str:
    return (
        f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
        f"/protocol/openid-connect/certs"
    )


def get_jwks() -> dict:
    """
    Return JWKS from cache or fetch from Keycloak
    """
    global jwks_cache, jwks_fetched_at

    now = time.monotonic()
    if jwks_cache and (now - jwks_fetched_at) < JWKS_TTL:
        return jwks_cache

    try:
        response = httpx.get(jwks_uri(), timeout=10)
        response.raise_for_status()
        jwks_cache = response.json()
        jwks_fetched_at = now
        log.info("JWKS refreshed from Keycloak")
        return jwks_cache
    except Exception as exc:
        log.error(f"Failed to fetch JWKS from Keycloak: {exc}")
        if jwks_cache:
            # Returns cache rather than failing completely
            log.warning("Returning stale JWKS cache")
            return jwks_cache
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )


# Token verification
def verify_token(token: str) -> dict:
    """
    Validate a JWT against the Keycloak JWKS
    """
    jwks = get_jwks()

    try:
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=KEYCLOAK_CLIENT_ID,
            options={"verify_aud": False}, 
        )
        return payload
    except JWTError as exc:
        log.warning(f"JWT validation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# FastAPI dependencies
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """
    Extracts and validates the Bearer token from the request,
    then returns the authenticated username
    """
    payload = verify_token(credentials.credentials)
    username = payload.get("preferred_username") or payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not contain a username claim",
        )
    return username


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme_optional
    ),
) -> str | None:
    """
    Returns the username if a valid Bearer token is present,
    or None if no token is provided
    """
    if not credentials:
        return None
    try:
        payload = verify_token(credentials.credentials)
        return payload.get("preferred_username") or payload.get("sub")
    except HTTPException:
        return None
