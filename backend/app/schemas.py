from pydantic import BaseModel, Field

from .models import ShareScope, Status


class Intake(BaseModel):
    one_sentence: str = Field("", max_length=400)
    leaning: str = Field("", max_length=400)
    afraid_of: str = Field("", max_length=2000)
    values: str = Field("", max_length=2000)
    constraints: str = Field("", max_length=2000)
    everything: str = Field("", max_length=8000)

    def is_empty(self) -> bool:
        return not any(
            v.strip()
            for v in (
                self.one_sentence,
                self.leaning,
                self.afraid_of,
                self.values,
                self.constraints,
                self.everything,
            )
        )


class CreateSessionResponse(BaseModel):
    id: str
    status: Status
    crisis: bool = False
    crisis_message: str | None = None


class ReplyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


class TurnOut(BaseModel):
    role: str
    content: str
    sequence: int


class VerdictOut(BaseModel):
    recommendation: str
    reasoning: str
    dissent: str
    next_actions: list[str]
    open_question: str


class SessionOut(BaseModel):
    id: str
    status: Status
    intake: Intake
    questions_asked: int
    turns: list[TurnOut]
    verdict: VerdictOut | None = None


class ShareRequest(BaseModel):
    scope: ShareScope = ShareScope.VERDICT_ONLY
    gallery: bool = False


class ShareResponse(BaseModel):
    token: str
    scope: ShareScope
    gallery: bool = False


class GalleryItem(BaseModel):
    token: str
    decision: str
    recommendation: str


class MeResponse(BaseModel):
    authenticated: bool
    oauth_enabled: bool
    name: str = ""
    email: str = ""
    picture: str = ""


class DocketItem(BaseModel):
    id: str
    decision: str
    status: str
    recommendation: str
    created_at: str


class SharedView(BaseModel):
    scope: ShareScope
    verdict: VerdictOut | None
    turns: list[TurnOut] | None = None
    decision: str = ""
