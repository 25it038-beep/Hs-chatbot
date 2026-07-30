from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.schemas.user import UserCreate
from app.utils.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: UserCreate) -> User:
        existing = await self.db.execute(
            select(User).where((User.email == data.email) | (User.username == data.username))
        )
        if existing.scalar_one_or_none():
            raise ValueError("Email or username already registered")
        user = User(
            email=data.email,
            username=data.username,
            hashed_password=hash_password(data.password),
            display_name=data.display_name or data.username,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def login(self, username: str, password: str) -> tuple[str, str, User]:
        result = await self.db.execute(
            select(User).where((User.username == username) | (User.email == username))
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")
        if not user.is_active:
            raise ValueError("Account is inactive")
        access_token = create_access_token({"sub": user.id, "username": user.username})
        refresh_token = create_refresh_token({"sub": user.id})
        return access_token, refresh_token, user

    async def refresh_token(self, token: str) -> tuple[str, str]:
        payload = decode_token(token)
        if payload is None or payload.get("type") != "refresh":
            raise ValueError("Invalid refresh token")
        user_id = payload.get("sub")
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")
        new_access = create_access_token({"sub": user.id, "username": user.username})
        new_refresh = create_refresh_token({"sub": user.id})
        return new_access, new_refresh

    async def get_user_by_id(self, user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
