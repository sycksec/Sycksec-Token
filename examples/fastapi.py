from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import os
import time
import logging
import uvicorn

# Setup logging
logging.basicConfig(level=logging.INFO)

# Import your SyckSec library (adjust if the import path is different)
from sycksec import SyckSec

app = FastAPI()

# FIXED: Set consistent fixed time for testing
if os.environ.get('SYCKSEC_ENV') == 'test':
    os.environ['SYCKSEC_FIXED_TIME'] = str(int(time.time()))

# Set secret (use environment variables in production for security)
os.environ['SYCKSEC_SECRET'] = 'YkcerGKipPVuhKnhP2IvL1gcFn8WwyW6'

# Initialize SyckSec client
sycksec = SyckSec()

# Define server-side custom recipe (kept internal, not exposed in API)
custom_recipe = {
    "version": "custom_secure_v1",
    "pattern": [10, "core", 15, "core", 8],  # Custom pattern with balanced noise
    "charset": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+",
    "randomize_noise": False,  # Deterministic (no randomness)
    "noise_variance": 0  # Fixed noise lengths
}

security = HTTPBearer(auto_error=False)

class LoginRequest(BaseModel):
    user_id: str
    device_fingerprint: Optional[str] = 'web_browser_123'
    location: Optional[str] = 'US'
    pattern: Optional[str] = 'standard'
    client_type: Optional[str] = 'web'

class NotesRequest(BaseModel):
    user_id: str

class RefreshRequest(BaseModel):
    user_id: str
    token: str

async def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), request: Request = None):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Token required")
    token = credentials.credentials
    try:
        body = await request.json()
    except:
        body = {}
    user_id = body.get('user_id')
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required in request body")
    try:
        # Use server-side custom recipe for verification
        payload = sycksec.verify(token, user_id, custom_recipe=custom_recipe)
        return payload
    except Exception as e:
        logging.error(f"Verification error: {str(e)}")  # Log errors for debugging
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/login")
async def login(data: LoginRequest):
    device_info = {
        "fingerprint": data.device_fingerprint,
        "location": data.location,
        "pattern": data.pattern,
        "client_type": data.client_type
    }
    try:
        # Use server-side custom recipe for generation
        token = sycksec.generate(data.user_id, ttl=3600, device_info=device_info, custom_recipe=custom_recipe)
        return {"token": token, "message": "Login successful"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/notes")  # POST to support body
async def get_notes(payload: dict = Depends(verify_token)):
    notes = [{"id": 1, "content": f"Secure note for {payload['user_id']}"}]
    return {"notes": notes, "device": payload["device_fingerprint"]}

@app.post("/refresh")
async def refresh(data: RefreshRequest, payload: dict = Depends(verify_token)):
    refreshed = sycksec.refresh_token_if_needed(data.token, data.user_id)
    if refreshed:
        return {"new_token": refreshed, "message": "Token refreshed"}
    return {"message": "Token still valid"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
