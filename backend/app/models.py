import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Status(str, enum.Enum):
    INTAKE = "intake"
    OPENING_PROS = "opening_pros"
    OPENING_DEF = "opening_def"
    JUDGE_Q = "judge_q"
    REBUTTAL_PROS = "rebuttal_pros"
    REBUTTAL_DEF = "rebuttal_def"
    VERDICT = "verdict"
    DONE = "done"
    CRISIS = "crisis"


class Role(str, enum.Enum):
    PROSECUTOR = "prosecutor"
    DEFENDER = "defender"
    JUDGE = "judge"
    USER = "user"
    SYSTEM = "system"


class ShareScope(str, enum.Enum):
    VERDICT_ONLY = "verdict_only"
    FULL = "full"


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    intake: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.INTAKE)
    model: Mapped[str] = mapped_column(String(128), default="")
    questions_asked: Mapped[int] = mapped_column(Integer, default=0)
    in_tokens: Mapped[int] = mapped_column(Integer, default=0)
    out_tokens: Mapped[int] = mapped_column(Integer, default=0)

    turns: Mapped[list["Turn"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Turn.sequence",
    )
    verdict: Mapped["Verdict | None"] = relationship(
        back_populates="session", cascade="all, delete-orphan", uselist=False
    )


class Turn(Base):
    __tablename__ = "turns"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    role: Mapped[Role] = mapped_column(Enum(Role))
    content: Mapped[str] = mapped_column(Text, default="")
    in_tokens: Mapped[int] = mapped_column(Integer, default=0)
    out_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped[Session] = relationship(back_populates="turns")


class Verdict(Base):
    __tablename__ = "verdicts"

    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    recommendation: Mapped[str] = mapped_column(Text, default="")
    reasoning: Mapped[str] = mapped_column(Text, default="")
    dissent: Mapped[str] = mapped_column(Text, default="")
    next_actions: Mapped[list] = mapped_column(JSON, default=list)
    open_question: Mapped[str] = mapped_column(Text, default="")
    raw: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped[Session] = relationship(back_populates="verdict")


class Share(Base):
    __tablename__ = "shares"

    token: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    scope: Mapped[ShareScope] = mapped_column(
        Enum(ShareScope), default=ShareScope.VERDICT_ONLY
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
