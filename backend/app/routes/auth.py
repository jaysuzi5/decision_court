import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import (
    STATE_COOKIE,
    clear_session,
    current_user_optional,
    set_session,
    sign_state,
    verify_state,
)
from ..config import get_settings
from ..db import get_db
from ..models import Session as DecisionSession
from ..models import User, Verdict
from ..oauth import authorize_url, exchange_code
from ..schemas import DocketItem, MeResponse

router = APIRouter(prefix="/api/auth")
settings = get_settings()


@router.get("/google/login")
async def google_login():
    if not settings.oauth_configured():
        raise HTTPException(503, "Google sign-in is not configured.")
    nonce = secrets.token_urlsafe(16)
    state = sign_state(nonce)
    resp = RedirectResponse(authorize_url(state))
    resp.set_cookie(
        STATE_COOKIE, state, max_age=600, httponly=True,
        secure=settings.cookie_secure, samesite="lax", path="/",
    )
    return resp


@router.get("/google/callback")
async def google_callback(
    request: Request, db: AsyncSession = Depends(get_db),
    code: str | None = None, state: str | None = None,
):
    cookie_state = request.cookies.get(STATE_COOKIE)
    if not code or not state or state != cookie_state or verify_state(state) is None:
        return RedirectResponse("/?auth=failed")
    info = await exchange_code(code)
    sub = info.get("sub")
    if not sub:
        return RedirectResponse("/?auth=failed")

    res = await db.execute(select(User).where(User.google_sub == sub))
    user = res.scalar_one_or_none()
    if user is None:
        user = User(google_sub=sub)
        db.add(user)
    user.email = info.get("email") or user.email
    user.name = info.get("name") or ""
    user.picture = info.get("picture") or ""
    await db.commit()

    resp = RedirectResponse("/")
    set_session(resp, user.id)
    resp.delete_cookie(STATE_COOKIE, path="/")
    return resp


@router.post("/logout")
async def logout():
    from fastapi.responses import JSONResponse
    resp = JSONResponse({"ok": True})
    clear_session(resp)
    return resp


@router.get("/me", response_model=MeResponse)
async def me(user: User | None = Depends(current_user_optional)):
    if not user:
        return MeResponse(authenticated=False, oauth_enabled=settings.oauth_configured())
    return MeResponse(
        authenticated=True, oauth_enabled=True,
        name=user.name, email=user.email or "", picture=user.picture,
    )


@router.get("/me/sessions", response_model=list[DocketItem])
async def my_sessions(
    user: User | None = Depends(current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    if not user:
        raise HTTPException(401, "Sign in to view your docket.")
    res = await db.execute(
        select(DecisionSession)
        .where(DecisionSession.user_id == user.id)
        .order_by(DecisionSession.created_at.desc())
        .limit(50)
    )
    items: list[DocketItem] = []
    for s in res.scalars().all():
        v = await db.get(Verdict, s.id)
        items.append(DocketItem(
            id=s.id,
            decision=(s.intake or {}).get("one_sentence", "") or "Untitled decision",
            status=s.status.value,
            recommendation=(v.recommendation if v else ""),
            created_at=s.created_at.isoformat(),
        ))
    return items
