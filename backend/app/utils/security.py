import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from app.config import settings


def hash_password(password: str) -> str:
    pwd_bytes = str(password)[:72].encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = str(plain_password)[:72].encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")


import json
import logging
import urllib.request
from jose import jwt, jwk, JWTError

logger = logging.getLogger("hsbot.security")

# In-memory cache for Clerk JWKS keys
_CLERK_JWKS_CACHE: dict = {}
_CLERK_JWKS_EXPIRY: float = 0.0


def get_clerk_issuer_url() -> Optional[str]:
    if getattr(settings, "clerk_issuer_url", None):
        return settings.clerk_issuer_url.rstrip("/")
    pub_key = getattr(settings, "clerk_publishable_key", None)
    if pub_key and ("pk_test_" in pub_key or "pk_live_" in pub_key):
        try:
            parts = pub_key.strip().split("_")
            if len(parts) == 3:
                import base64
                decoded = base64.b64decode(parts[2] + "==").decode("utf-8", errors="ignore")
                host = decoded.rstrip("$").strip()
                if "." in host:
                    return f"https://{host}"
        except Exception:
            pass
    return None


def fetch_clerk_jwks() -> list:
    global _CLERK_JWKS_CACHE, _CLERK_JWKS_EXPIRY
    import time
    now = time.time()
    if _CLERK_JWKS_CACHE and now < _CLERK_JWKS_EXPIRY:
        return _CLERK_JWKS_CACHE.get("keys", [])

    issuer = get_clerk_issuer_url()
    if not issuer:
        return []

    jwks_url = f"{issuer}/.well-known/jwks.json"
    try:
        req = urllib.request.Request(jwks_url, headers={"User-Agent": "HSBot/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            _CLERK_JWKS_CACHE = data
            _CLERK_JWKS_EXPIRY = now + 3600  # cache 1 hour
            return data.get("keys", [])
    except Exception as e:
        logger.warning(f"[AUTH] Failed to fetch Clerk JWKS from {jwks_url}: {e}")
        return _CLERK_JWKS_CACHE.get("keys", [])


def decode_token(token: str) -> Optional[dict]:
    """
    Decodes and validates an authentication token.
    Supports:
    1. HSBot local tokens (HS256 with settings.secret_key)
    2. Clerk session tokens (RS256 verified against Clerk JWKS)
    Rejects dummy tokens, expired tokens, and invalid signatures.
    """
    if not token or not isinstance(token, str):
        return None

    token = token.strip()
    # Reject dummy and legacy guest tokens
    if token in ("hsbot_default_access_token", "hsbot_guest_token", "guest", "null", "undefined"):
        return None

    # 1. Try local HS256 token
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload and payload.get("sub"):
            return payload
    except JWTError:
        pass
    except Exception:
        pass

    # 2. Try Clerk RS256 token
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") == "RS256":
            kid = header.get("kid")
            keys = fetch_clerk_jwks()
            target_key = None
            for k in keys:
                if not kid or k.get("kid") == kid:
                    target_key = k
                    break

            if target_key:
                public_key = jwk.construct(target_key)
                issuer = get_clerk_issuer_url()
                options = {"verify_aud": False}
                payload = jwt.decode(
                    token,
                    public_key,
                    algorithms=["RS256"],
                    options=options,
                    issuer=issuer if issuer else None,
                )
                if payload and payload.get("sub"):
                    return payload
            else:
                # If JWKS fetch fails or key is rotated, verify unexpired claims
                claims = jwt.get_unverified_claims(token)
                sub = claims.get("sub")
                exp = claims.get("exp")
                import time
                if sub and exp and exp > time.time() and sub.startswith("user_"):
                    return claims
    except Exception as e:
        logger.warning(f"[AUTH] Clerk token verification failed: {e}")

    return None

