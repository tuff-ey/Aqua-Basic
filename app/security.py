from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

VALID_API_KEYS = {
    "google": "123",
    "app": "xnDlV7niyfZ1TlpXPg2SHXNfzdU1sicnlNSweFY4vMxSEW2bBa8EZkWHQAJfGbckUqG2WYmWpH4wVZuw9vf5rrAcIzclw93hKDOuvDMbt7iBo8m7DWDAES8dfV13kpCXKdRwWnp1wlE06k0DRaupVRfysGwGCdj2Tf2iWgwQAytxrdkEemg5cw1TbTxeYb5Aprt6yacvgmyNZ0KD8HP236ar5zKnCJ7TTdt6vXn2KGVBQPDuaFE7KItNCKcLrmQB"
}

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key not in VALID_API_KEYS.values():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )