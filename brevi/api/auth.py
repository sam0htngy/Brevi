import os
from functools import lru_cache

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt import PyJWKClient

security = HTTPBearer()


@lru_cache(maxsize=1)
def _jwks_client(issuer: str) -> PyJWKClient:
    return PyJWKClient(f"{issuer}/.well-known/jwks.json")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """Verify the Clerk bearer token and return its claims."""
    try:
        token = credentials.credentials
        domain = os.getenv("CLERK_DOMAIN", "").removeprefix("https://").rstrip("/")
        if not domain:
            raise RuntimeError("CLERK_DOMAIN must be configured")
        issuer = f"https://{domain}"
        audience = os.getenv("CLERK_AUDIENCE") or None
        signing_key = _jwks_client(issuer).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token, signing_key.key, algorithms=["RS256"], issuer=issuer,
            audience=audience, options={"verify_aud": audience is not None},
        )
        if not claims.get("sub"):
            raise jwt.InvalidTokenError("Token has no subject")
        return claims
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired login token") from exc
