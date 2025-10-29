import os
import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Optional


security = HTTPBearer()
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL")
if not SUPABASE_JWT_SECRET:
    raise ValueError("SUPABASE_JWT_SECRET enviroment variable is not set")

def verify_jwt_token(token :str) -> dict:
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            alorgithms = ['HS256'],
            audience= "authenticated",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail = "Token has expired",
            headrsd = {"WWW-Authenticate": "Bearer"},
        )
        
def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict: