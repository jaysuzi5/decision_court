import logging
import asyncio
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import SessionLocal, get_db
from ..models import Role, Session, Status, Turn
from .. import metrics
from ..orchestrator import load_session, run
from ..ratelimit import SlidingWindowLimiter
from ..safety import crisis_response, detect_crisis
from ..schemas import (
    CreateSessionResponse,
    Intake,
    ReplyRequest,
    SessionOut,
    TurnOut,
    VerdictOut,
)
from ..sse import format_sse, to_sse
from ..transcript import full_transcript_md

router = APIRouter(prefix="/api")
settings = get_settings()

# Per-session generation lock: prevents two stream connections double-driving one session.
_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

_limiter = SlidingWindowLimiter(settings.rate_limit_sessions, settings.rate_limit_window_sec)


def _client_ip(request: Request) -> str:
    # Behind cloudflared/nginx: trust the first X-Forwarded-For hop, else the socket peer.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _intake_text(intake: Intake) -> str:
    return " ".join(
        [intake.one_sentence, intake.leaning, intake.afraid_of,
         intake.values, intake.constraints, intake.everything]
    )


@router.post("/session", response_model=CreateSessionResponse)
async def create_session(
    intake: Intake, request: Request, db: AsyncSession = Depends(get_db)
):
    if not _limiter.allow(_client_ip(request)):
        metrics.rate_limited.inc()
        retry = _limiter.retry_after(_client_ip(request))
        raise HTTPException(
            429,
            f"The docket is full from your address — try again in about "
            f"{max(1, retry // 60)} minute(s).",
            headers={"Retry-After": str(retry)},
        )
    if intake.is_empty():
        raise HTTPException(422, "Tell the court about your decision first.")
    session = Session(intake=intake.model_dump(), model=settings.debate_model())
    if detect_crisis(_intake_text(intake)):
        session.status = Status.CRISIS
        db.add(session)
        await db.commit()
        metrics.sessions_created.labels(crisis="true").inc()
        metrics.crisis_triggered.labels(stage="intake").inc()
        return CreateSessionResponse(
            id=session.id, status=session.status, crisis=True,
            crisis_message=crisis_response(settings.crisis_region),
        )
    session.status = Status.OPENING_PROS
    db.add(session)
    await db.commit()
    metrics.sessions_created.labels(crisis="false").inc()
    return CreateSessionResponse(id=session.id, status=session.status)


def _to_out(session: Session) -> SessionOut:
    v = session.verdict
    return SessionOut(
        id=session.id,
        status=session.status,
        intake=Intake(**session.intake),
        questions_asked=session.questions_asked,
        turns=[
            TurnOut(role=t.role.value, content=t.content, sequence=t.sequence)
            for t in session.turns
            if t.role != Role.SYSTEM
        ],
        verdict=VerdictOut(
            recommendation=v.recommendation, reasoning=v.reasoning, dissent=v.dissent,
            next_actions=v.next_actions, open_question=v.open_question,
        ) if v else None,
    )


@router.get("/session/{session_id}", response_model=SessionOut)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await load_session(db, session_id)
    if not session:
        raise HTTPException(404, "No such case.")
    return _to_out(session)


@router.get("/session/{session_id}/markdown")
async def get_markdown(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await load_session(db, session_id)
    if not session:
        raise HTTPException(404, "No such case.")
    md = full_transcript_md(session, include_intake=True)
    return Response(md, media_type="text/markdown")


@router.delete("/session/{session_id}", status_code=204)
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await load_session(db, session_id)
    if not session:
        raise HTTPException(404, "No such case.")
    await db.delete(session)
    await db.commit()
    _locks.pop(session_id, None)
    return Response(status_code=204)


@router.post("/session/{session_id}/reply", response_model=SessionOut)
async def reply(session_id: str, body: ReplyRequest, db: AsyncSession = Depends(get_db)):
    session = await load_session(db, session_id)
    if not session:
        raise HTTPException(404, "No such case.")
    if session.status == Status.CRISIS:
        raise HTTPException(409, "This session is paused for safety.")
    if session.status != Status.JUDGE_Q or not (
        session.turns and session.turns[-1].role == Role.JUDGE
    ):
        raise HTTPException(409, "The court is not waiting for your answer right now.")

    if detect_crisis(body.text):
        session.status = Status.CRISIS
        await db.commit()
        metrics.crisis_triggered.labels(stage="reply").inc()
        raise HTTPException(
            423, detail={"crisis": True, "message": crisis_response(settings.crisis_region)}
        )

    turn = Turn(
        session_id=session.id, sequence=len(session.turns),
        role=Role.USER, content=body.text.strip(),
    )
    db.add(turn)
    session.turns.append(turn)
    await db.commit()
    return _to_out(session)


@router.get("/session/{session_id}/stream")
async def stream(session_id: str, db: AsyncSession = Depends(get_db)):
    # Existence check on the request-scoped session; streaming uses its own session
    # (below) so its lifetime spans the whole SSE body, not just this function call.
    if not await load_session(db, session_id):
        raise HTTPException(404, "No such case.")

    async def gen():
        async with SessionLocal() as sdb:
            session = await load_session(sdb, session_id)
            if not session:
                yield format_sse("error", {"message": "No such case."})
                return
            # Replay persisted state first so a reconnecting client can rebuild the room.
            yield format_sse("history", {
                "status": session.status.value,
                "turns": [
                    {"role": t.role.value, "content": t.content, "sequence": t.sequence}
                    for t in session.turns if t.role != Role.SYSTEM
                ],
                "questions_asked": session.questions_asked,
                "verdict": (lambda v: v and {
                    "recommendation": v.recommendation, "reasoning": v.reasoning,
                    "dissent": v.dissent, "next_actions": v.next_actions,
                    "open_question": v.open_question,
                })(session.verdict),
            })
            lock = _locks[session_id]
            if lock.locked():
                yield format_sse("busy", {})
                return
            async with lock:
                try:
                    async for chunk in to_sse(run(sdb, session)):
                        yield chunk
                except Exception:
                    logging.getLogger("decision_court").exception("stream failed")
                    await sdb.rollback()
                    yield format_sse("error", {"message": "The court was interrupted. Reconnecting will resume."})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
