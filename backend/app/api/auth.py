"""Authentication endpoints."""

from fastapi import APIRouter, HTTPException

from app.models.user import User
from app.core.auth import verify_password, create_access_token

router = APIRouter()


@router.post("/api/auth/login")
async def login(data: dict):
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user = await User.filter(username=username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(user.id, user.username)
    return {"token": token, "username": user.username}
