import uuid
import logging
from typing import Optional
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.utils.security import decode_token, hash_password

logger = logging.getLogger("hsbot.auth")
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Strict authentication dependency.
    Requires a valid JWT token (HSBot HS256 or Clerk RS256).
    Rejects anonymous, guest, and expired tokens with HTTP 401.
    Guarantees that every authenticated user receives their own isolated User record.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or unauthorized authentication token. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = str(payload.get("sub")).strip()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token: missing subject identity.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Lookup user in database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        # Auto-provision isolated User record for new verified identities (e.g. Clerk or test identities)
        raw_username = payload.get("username") or (payload.get("email") or "").split("@")[0] or user_id
        raw_email = payload.get("email") or f"{user_id}@hsbot.local"
        display_name = payload.get("name") or payload.get("display_name") or raw_username

        # Deduplicate username/email if collision with existing account
        clean_username = str(raw_username)[:30]
        clean_email = str(raw_email)[:255]

        # Check for unique email constraint collision
        existing_email_res = await db.execute(select(User).where(User.email == clean_email))
        if existing_email_res.scalar_one_or_none():
            clean_email = f"{user_id}_{clean_email}"[:255]

        # Check for unique username constraint collision
        existing_user_res = await db.execute(select(User).where(User.username == clean_username))
        if existing_user_res.scalar_one_or_none():
            clean_username = f"{clean_username[:20]}_{uuid.uuid4().hex[:8]}"

        user = User(
            id=user_id,
            email=clean_email,
            username=clean_username,
            hashed_password=hash_password(uuid.uuid4().hex),
            display_name=display_name,
            is_active=True,
        )
        try:
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info("[AUTH] Provisioned new isolated user space for user_id=%s", user_id)
        except Exception as e:
            await db.rollback()
            # If created concurrently
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                logger.error("[AUTH] Failed to initialize user space: %s", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to initialize user session space.",
                )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Returns the authenticated User if a valid token is provided,
    or None if no authentication is present.
    NEVER falls back to a shared default user.
    """
    if not credentials or not credentials.credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None

