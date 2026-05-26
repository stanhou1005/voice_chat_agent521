"""Authentication and user management endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.models.user import User
from app.core.auth import verify_password, create_access_token, hash_password, get_current_user, get_current_admin

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

    token = create_access_token(user.id, user.username, user.role)
    return {"token": token, "username": user.username, "role": user.role}


# ─── User management (admin only) ────────────────────────

@router.get("/api/auth/users")
async def list_users(user: dict = Depends(get_current_admin)):
    users = await User.all().values("id", "username", "role", "created_at")
    return {"users": list(users)}


@router.post("/api/auth/users")
async def create_user(data: dict, user: dict = Depends(get_current_admin)):
    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "user")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    if role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Role must be admin or user")

    existing = await User.filter(username=username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    await User.create(username=username, password_hash=hash_password(password), role=role)
    return {"status": "ok", "username": username, "role": role}


@router.delete("/api/auth/users/{user_id}")
async def delete_user(user_id: int, user: dict = Depends(get_current_admin)):
    if str(user_id) == user.get("sub"):
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    target = await User.filter(id=user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    await target.delete()
    return {"status": "ok"}
