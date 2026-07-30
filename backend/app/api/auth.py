from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.user import UserCreate, UserResponse, LoginRequest, TokenResponse, RefreshRequest, UserUpdate
from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.auth import AuthService
from app.utils.security import create_access_token, create_refresh_token, decode_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    auth = AuthService(db)
    try:
        user = await auth.register(data)
        access = create_access_token({"sub": user.id, "username": user.username})
        refresh = create_refresh_token({"sub": user.id})
        return TokenResponse(access_token=access, refresh_token=refresh, user=UserResponse.model_validate(user))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    auth = AuthService(db)
    try:
        access, refresh, user = await auth.login(data.username, data.password)
        return TokenResponse(access_token=access, refresh_token=refresh, user=UserResponse.model_validate(user))
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    auth = AuthService(db)
    try:
        access, refresh = await auth.refresh_token(data.refresh_token)
        payload = decode_token(access)
        user = await auth.get_user_by_id(payload["sub"])
        return TokenResponse(access_token=access, refresh_token=refresh, user=UserResponse.model_validate(user))
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_me(data: UserUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)
