import httpx
from jose import jwt, jwk, JWTError
from fastapi import HTTPException, Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import os

CLERK_DOMAIN = os.getenv("CLERK_DOMAIN")
JWKS_URL = f"https://{CLERK_DOMAIN}/.well-kown/jwks.json"
ISSUER = f"https://{CLERK_DOMAIN}"

class ClerkTokenVerifier:
    def __init__(self):
        self.jwks = None
        
    async def get_jwks(self, force_refresh = False):
        if self.jwks is None or force_refresh:
            async with httpx.AsyncClient() as client:
                response = await client.get() # get the JWT KEY URL
                self.jwks = response.json()
                
        return self.jwks
    
    async def verify(self, token: str) -> dict:
        try:
            return await self._verify_logic(token, force_refresh= False)
        except JWTError:
            return await self._verify_logic(token, force_refresh = True)
        
    async def _verify_logic(self, token: dict, force_refresh: bool ):
        key = await self.get_jwks(force_refresh)
        
        header = jwt.get_unverified_header(token)
        rsa_key = next((k for k in key ["key"] if k["kid"] == header ["kid"]), None)
        
        if not rsa_key:
            raise JWTError("Key not found")
        
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            issuer = ISSUER
        )
        return payload

auth_handle = ClerkTokenVerifier()
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    token = credentials.credentials
    try: 
        payload = await auth_handle.verify(token)
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail= "Failed to login")
        
        