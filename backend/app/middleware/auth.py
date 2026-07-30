import uuid
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.utils.security import decode_token, hash_password

security = HTTPBearer(auto_error=False)

DEFAULT_USER_ID = "default_user_id"


async def get_or_create_default_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == DEFAULT_USER_ID))
    user = result.scalar_one_or_none()
    if user:
        return user

    result = await db.execute(select(User).order_by(User.created_at).limit(1))
    user = result.scalar_one_or_none()
    if user:
        return user

    try:
        user = User(
            id=DEFAULT_USER_ID,
            email=f"default_{uuid.uuid4().hex[:8]}@hsbot.ai",
            username=f"hsbot_user_{uuid.uuid4().hex[:8]}",
            hashed_password=hash_password("hsbot_default_pass"),
            display_name="HSBot User",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    except Exception:
        await db.rollback()
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if user:
            return user
        raise HTTPException(status_code=500, detail="Database default user initialization failed")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        if credentials and credentials.credentials:
            token = credentials.credentials
            payload = decode_token(token)
            if payload and payload.get("type") == "access":
                user_id = payload.get("sub")
                if user_id:
                    result = await db.execute(select(User).where(User.id == user_id))
                    user = result.scalar_one_or_none()
                    if user and user.is_active:
                        return user
    except Exception:
        pass

    return await get_or_create_default_user(db)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    return await get_current_user(credentials, db)
