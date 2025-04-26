from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

VALID_API_KEYS = {
    "User1": "qwerty",
    "User2": "uiop"
}

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key not in VALID_API_KEYS.values():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )