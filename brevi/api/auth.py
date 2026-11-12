import os
from functools import lru_cache

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt import PyJWKClient

CLERK_DOMAIN = os.getenv("CLERK_DOMAIN", "").removeprefix("https://").rstrip("/")
CLERK_ISSUER = f"https://{CLERK_DOMAIN}" if CLERK_DOMAIN else ""
CLERK_AUDIENCE = os.getenv("CLERK_AUDIENCE") or None
security = HTTPBearer()


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    if not CLERK_DOMAIN:
        raise RuntimeError("CLERK_DOMAIN must be configured")
    return PyJWKClient(f"{CLERK_ISSUER}/.well-known/jwks.json")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """Verify the Clerk bearer token and return its claims."""
    try:
        token = credentials.credentials
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token, signing_key.key, algorithms=["RS256"], issuer=CLERK_ISSUER,
            audience=CLERK_AUDIENCE, options={"verify_aud": CLERK_AUDIENCE is not None},
        )
        if not claims.get("sub"):
            raise jwt.InvalidTokenError("Token has no subject")
        return claims
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired login token") from exc
