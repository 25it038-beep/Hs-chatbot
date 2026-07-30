import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

db_url = settings.database_url
if db_url.startswith("sqlite"):
    clean_path = db_url.split("///")[-1]
    if clean_path and clean_path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(clean_path)), exist_ok=True)

engine = create_async_engine(db_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    import app.models  # noqa: F401 - ensure all ORM models are registered
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        try:
            from app.models.user import User
            from app.utils.security import hash_password
            from sqlalchemy import select
            result = await session.execute(select(User).where(User.id == "default_user_id"))
            if not result.scalar_one_or_none():
                user = User(
                    id="default_user_id",
                    email="user@hsbot.ai",
                    username="hsbot_user",
                    hashed_password=hash_password("hsbot_default_pass"),
                    display_name="HSBot User",
                    is_active=True,
                )
                session.add(user)
                await session.commit()
        except Exception:
            await session.rollback()
