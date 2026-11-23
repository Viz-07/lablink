import base64
import hashlib
import hmac
import json
import time
from secrets import token_hex

from ..domain.models import User
from .config import Settings


def b64(value: bytes) -> str:
    """Encode bytes as unpadded URL-safe Base64."""
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def decode(value: str) -> bytes:
    """Decode and validate unpadded URL-safe Base64."""
    return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)


HEADER = b64(b'{"alg":"HS256","typ":"JWT"}')


def signature(message: str, key: str) -> str:
    """Compute the URL-safe HMAC-SHA256 signature of a message."""
    return b64(hmac.digest(key.encode(), message.encode(), hashlib.sha256))


def new_token(settings: Settings, user: User) -> str:
    """Issue a signed session token with an expiry."""
    now = int(time.time())
    body = b64(
        json.dumps(
            {
                "sub": user.id,
                "role": user.role.value,
                "iat": now,
                "exp": now + settings.session_ttl_minutes * 60,
                "jti": token_hex(16),
            },
            separators=(",", ":"),
        ).encode()
    )
    message = f"{HEADER}.{body}"
    return f"{message}.{signature(message, settings.session_secret)}"


def token_user(settings: Settings, token: str | None) -> str | None:
    """Return the user identifier from a valid, unexpired session token."""
    if not token or len(token) > 2048:
        return None
    try:
        header, payload, supplied = token.split(".")
        if header != HEADER or not hmac.compare_digest(
            signature(f"{header}.{payload}", settings.session_secret), supplied
        ):
            return None
        data = json.loads(decode(payload))
        if (
            type(data["exp"]) is int
            and type(data["iat"]) is int
            and data["iat"] <= time.time() < data["exp"]
            and isinstance(data["sub"], str)
        ):
            return data["sub"]
    except (ValueError, TypeError, KeyError):
        return None
    return None
