from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Role, Share, ShareScope, Status
from ..orchestrator import load_session
from ..schemas import (
    ShareRequest,
    ShareResponse,
    SharedView,
    TurnOut,
    VerdictOut,
)
from ..transcript import full_transcript_md

router = APIRouter(prefix="/api")


@router.post("/session/{session_id}/share", response_model=ShareResponse)
async def create_share(
    session_id: str, body: ShareRequest, db: AsyncSession = Depends(get_db)
):
    session = await load_session(db, session_id)
    if not session:
        raise HTTPException(404, "No such case.")
    if session.status != Status.DONE:
        raise HTTPException(409, "There is no verdict to share yet.")
    share = Share(session_id=session.id, scope=body.scope)
    db.add(share)
    await db.commit()
    return ShareResponse(token=share.token, scope=share.scope)


async def _load_share(db: AsyncSession, token: str) -> tuple[Share, object]:
    res = await db.execute(select(Share).where(Share.token == token))
    share = res.scalar_one_or_none()
    if not share:
        raise HTTPException(404, "This shared verdict was not found.")
    session = await load_session(db, share.session_id)
    if not session:
        raise HTTPException(404, "This shared verdict was not found.")
    return share, session


@router.get("/share/{token}", response_model=SharedView)
async def view_share(token: str, db: AsyncSession = Depends(get_db)):
    share, session = await _load_share(db, token)
    v = session.verdict
    verdict = VerdictOut(
        recommendation=v.recommendation, reasoning=v.reasoning, dissent=v.dissent,
        next_actions=v.next_actions, open_question=v.open_question,
    ) if v else None
    turns = None
    if share.scope == ShareScope.FULL:
        turns = [
            TurnOut(role=t.role.value, content=t.content, sequence=t.sequence)
            for t in session.turns if t.role != Role.SYSTEM
        ]
    return SharedView(
        scope=share.scope, verdict=verdict, turns=turns,
        decision=(session.intake or {}).get("one_sentence", "") if share.scope == ShareScope.FULL else "",
    )


@router.get("/share/{token}/markdown")
async def share_markdown(token: str, db: AsyncSession = Depends(get_db)):
    share, session = await _load_share(db, token)
    # Default share scope NEVER exposes raw intake.
    if share.scope == ShareScope.FULL:
        md = full_transcript_md(session, include_intake=True)
    else:
        from ..transcript import verdict_md
        md = "# Decision Court — Verdict\n\n" + verdict_md(session)
    return Response(md, media_type="text/markdown")
