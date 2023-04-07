from fastapi import Header, HTTPException
import os

async def get_auth(token: str = Header(None)):
    if os.getenv('MASTER_TOKEN') == token:
        return token
    
    else:
        raise HTTPException(status_code=400, detail="token is wrong")
