"""Server-side orchestrator. Drives the proceeding as a state machine and streams
agent turns. `status` always names the NEXT step to run; it advances only after a turn
is persisted, so a dropped connection simply regenerates the in-flight step (resumable,
idempotent). The Judge-question step pauses for a user reply."""

import re
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .agents import case_file, system_prompt
from .config import get_settings
from .groq_client import StreamResult, stream_chat
from .models import Role, Session, Status, Turn, Verdict
from .schemas import Intake

settings = get_settings()

ROLE_LABEL = {
    Role.PROSECUTOR: "PROSECUTOR",
    Role.DEFENDER: "DEFENDER",
    Role.JUDGE: "JUDGE",
    Role.USER: "PETITIONER",
}

TEMPERATURE = {
    "opening": 0.9,
    "judge_q": 0.6,
    "rebuttal": 0.9,
    "verdict": 0.5,
}


def _transcript(turns: list[Turn]) -> str:
    if not turns:
        return "(no statements yet)"
    return "\n\n".join(f"### {ROLE_LABEL.get(t.role, t.role.value)}\n{t.content}" for t in turns)


def _user_block(intake: Intake, turns: list[Turn], instruction: str) -> str:
    return (
        f"{case_file(intake)}\n\n## TRANSCRIPT SO FAR\n{_transcript(turns)}\n\n"
        f"## YOUR TASK\n{instruction}"
    )


def _sse(event: str, **data) -> dict:
    return {"event": event, "data": data}


async def _persist_turn(
    db: AsyncSession, session: Session, role: Role, content: str, res: StreamResult
) -> Turn:
    seq = len(session.turns)
    turn = Turn(
        session_id=session.id,
        sequence=seq,
        role=role,
        content=content,
        in_tokens=res.in_tokens,
        out_tokens=res.out_tokens,
    )
    db.add(turn)
    session.in_tokens += res.in_tokens
    session.out_tokens += res.out_tokens
    session.turns.append(turn)
    return turn


async def _generate(
    db: AsyncSession,
    session: Session,
    *,
    persona: str,
    role: Role,
    instruction: str,
    temperature: float,
    model: str,
    extra_system: str = "",
) -> AsyncIterator[dict]:
    """Stream one agent turn, emit deltas, persist on completion."""
    intake = Intake(**session.intake)
    messages = [
        {"role": "system", "content": system_prompt(persona, extra=extra_system)},
        {"role": "user", "content": _user_block(intake, session.turns, instruction)},
    ]
    res = StreamResult()
    buf: list[str] = []
    yield _sse("phase_start", role=role.value)
    async for delta in stream_chat(
        model=model,
        messages=messages,
        max_tokens=settings.max_tokens_per_turn,
        temperature=temperature,
        result=res,
    ):
        buf.append(delta)
        yield _sse("delta", role=role.value, text=delta)
    content = "".join(buf).strip()
    turn = await _persist_turn(db, session, role, content, res)
    await db.commit()
    yield _sse("turn_complete", role=role.value, sequence=turn.sequence)


_VERDICT_INSTRUCTION = (
    "Deliver your VERDICT now. Output EXACTLY these markdown sections, in this order, "
    "with these headers verbatim:\n\n"
    "## Recommendation\n<your clear call>\n\n"
    "## Reasoning\n<your reasoning>\n\n"
    "## Dissent\n<the strongest fair case for the path you did NOT choose>\n\n"
    "## Next actions\n- <action 1>\n- <action 2>\n- <action 3 (optional)>\n\n"
    "## Open question\n<the one question only they can answer>"
)


def _section(raw: str, header: str, nexts: list[str]) -> str:
    stop = "|".join(re.escape(h) for h in nexts) or r"\Z"
    m = re.search(
        rf"##\s*{re.escape(header)}\s*\n(.*?)(?=\n##\s*(?:{stop})|\Z)",
        raw,
        re.IGNORECASE | re.DOTALL,
    )
    return m.group(1).strip() if m else ""


def parse_verdict(raw: str) -> dict:
    rec = _section(raw, "Recommendation", ["Reasoning", "Dissent", "Next actions", "Open question"])
    reasoning = _section(raw, "Reasoning", ["Dissent", "Next actions", "Open question"])
    dissent = _section(raw, "Dissent", ["Next actions", "Open question"])
    actions_raw = _section(raw, "Next actions", ["Open question"])
    open_q = _section(raw, "Open question", [])
    actions = [
        re.sub(r"^[-*\d.\)\s]+", "", ln).strip()
        for ln in actions_raw.splitlines()
        if ln.strip()
    ]
    actions = [a for a in actions if a]
    return {
        "recommendation": rec or raw.strip()[:500],
        "reasoning": reasoning,
        "dissent": dissent,
        "next_actions": actions,
        "open_question": open_q,
    }


async def _run_verdict(db: AsyncSession, session: Session) -> AsyncIterator[dict]:
    intake = Intake(**session.intake)
    messages = [
        {"role": "system", "content": system_prompt("judge", extra="Mode: VERDICT")},
        {"role": "user", "content": _user_block(intake, session.turns, _VERDICT_INSTRUCTION)},
    ]
    res = StreamResult()
    buf: list[str] = []
    yield _sse("phase_start", role="judge", phase="verdict")
    async for delta in stream_chat(
        model=settings.verdict_model(),
        messages=messages,
        max_tokens=max(settings.max_tokens_per_turn, 1100),
        temperature=TEMPERATURE["verdict"],
        result=res,
    ):
        buf.append(delta)
        yield _sse("delta", role="judge", text=delta)
    raw = "".join(buf).strip()
    parsed = parse_verdict(raw)
    await _persist_turn(db, session, Role.JUDGE, raw, res)
    db.add(Verdict(session_id=session.id, raw=raw, **parsed))
    session.status = Status.DONE
    await db.commit()
    yield _sse("turn_complete", role="judge", sequence=session.turns[-1].sequence)
    yield _sse("verdict", **parsed)


def _awaiting_reply(session: Session) -> bool:
    return (
        session.status == Status.JUDGE_Q
        and bool(session.turns)
        and session.turns[-1].role == Role.JUDGE
    )


async def run(db: AsyncSession, session: Session) -> AsyncIterator[dict]:
    """Advance the proceeding from the current status until a pause (await reply),
    DONE, or CRISIS. Yields SSE event dicts."""
    if session.status == Status.CRISIS:
        yield _sse("crisis")
        return

    while True:
        # Cost guardrail: out of budget -> jump straight to verdict so user still gets one.
        if (
            session.out_tokens >= settings.max_tokens_per_session
            and session.status not in (Status.VERDICT, Status.DONE, Status.CRISIS)
        ):
            yield _sse("wrapping_up")
            session.status = Status.VERDICT
            await db.commit()

        st = session.status

        if st == Status.DONE:
            yield _sse("done")
            return

        if st in (Status.INTAKE, Status.OPENING_PROS):
            async for ev in _generate(
                db, session, persona="prosecutor", role=Role.PROSECUTOR,
                instruction="Deliver your opening statement now.",
                temperature=TEMPERATURE["opening"], model=settings.debate_model(),
            ):
                yield ev
            session.status = Status.OPENING_DEF
            await db.commit()

        elif st == Status.OPENING_DEF:
            async for ev in _generate(
                db, session, persona="defender", role=Role.DEFENDER,
                instruction="Deliver your opening statement now, answering the Prosecutor where useful.",
                temperature=TEMPERATURE["opening"], model=settings.debate_model(),
            ):
                yield ev
            session.status = Status.JUDGE_Q
            await db.commit()

        elif st == Status.JUDGE_Q:
            if _awaiting_reply(session):
                yield _sse(
                    "await_reply",
                    question_number=session.questions_asked,
                    max_questions=settings.max_judge_questions,
                )
                return
            if session.questions_asked >= settings.max_judge_questions:
                session.status = Status.REBUTTAL_PROS
                await db.commit()
                continue
            n = session.questions_asked + 1
            async for ev in _generate(
                db, session, persona="judge", role=Role.JUDGE,
                instruction=(
                    f"Ask your next cross-examination question (question {n} of up to "
                    f"{settings.max_judge_questions}). One question only."
                ),
                temperature=TEMPERATURE["judge_q"], model=settings.debate_model(),
                extra_system="Mode: CROSS_EXAMINATION",
            ):
                yield ev
            session.questions_asked = n
            await db.commit()
            yield _sse(
                "await_reply",
                question_number=n,
                max_questions=settings.max_judge_questions,
            )
            return

        elif st == Status.REBUTTAL_PROS:
            async for ev in _generate(
                db, session, persona="prosecutor", role=Role.PROSECUTOR,
                instruction=(
                    "Deliver your rebuttal. Respond to what the petitioner revealed under "
                    "questioning and attack the Defender's strongest point."
                ),
                temperature=TEMPERATURE["rebuttal"], model=settings.debate_model(),
            ):
                yield ev
            session.status = Status.REBUTTAL_DEF
            await db.commit()

        elif st == Status.REBUTTAL_DEF:
            async for ev in _generate(
                db, session, persona="defender", role=Role.DEFENDER,
                instruction=(
                    "Deliver your rebuttal. Respond to what the petitioner revealed and "
                    "answer the Prosecutor's strongest attack."
                ),
                temperature=TEMPERATURE["rebuttal"], model=settings.debate_model(),
            ):
                yield ev
            session.status = Status.VERDICT
            await db.commit()

        elif st == Status.VERDICT:
            async for ev in _run_verdict(db, session):
                yield ev
            # status set to DONE inside _run_verdict

        else:
            return


async def load_session(db: AsyncSession, session_id: str) -> Session | None:
    res = await db.execute(
        select(Session)
        .where(Session.id == session_id)
        .options(selectinload(Session.turns), selectinload(Session.verdict))
    )
    return res.scalar_one_or_none()
