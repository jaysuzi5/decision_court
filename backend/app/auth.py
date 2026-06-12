"""Session cookie (signed, httponly) + current-user dependencies. Stateless: the
cookie carries the signed user id; we load the User row per request."""

from fastapi import Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .db import get_db
from .models import User

settings = get_settings()
COOKIE = "dc_session"
STATE_COOKIE = "dc_oauth_state"

_serializer = URLSafeTimedSerializer(settings.session_secret, salt="dc-session")
_state_serializer = URLSafeTimedSerializer(settings.session_secret, salt="dc-oauth-state")


def set_session(response: Response, user_id: str) -> None:
    response.set_cookie(
        COOKIE,
        _serializer.dumps(user_id),
        max_age=settings.session_max_age_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")


def sign_state(value: str) -> str:
    return _state_serializer.dumps(value)


def verify_state(token: str) -> str | None:
    try:
        return _state_serializer.loads(token, max_age=600)
    except (BadSignature, SignatureExpired):
        return None


def _uid_from_request(request: Request) -> str | None:
    raw = request.cookies.get(COOKIE)
    if not raw:
        return None
    try:
        return _serializer.loads(raw, max_age=settings.session_max_age_days * 86400)
    except (BadSignature, SignatureExpired):
        return None


async def current_user_optional(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User | None:
    uid = _uid_from_request(request)
    if not uid:
        return None
    return await db.get(User, uid)


async def current_user(
    user: User | None = Depends(current_user_optional),
) -> User:
    if user is None:
        raise HTTPException(401, "Sign in to view this.")
    return user
