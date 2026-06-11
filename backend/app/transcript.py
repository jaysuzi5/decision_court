from .models import Role, Session
from .orchestrator import ROLE_LABEL


def _intake_md(intake: dict) -> str:
    rows = [
        ("Decision", intake.get("one_sentence")),
        ("Leaning toward", intake.get("leaning")),
        ("Afraid of", intake.get("afraid_of")),
        ("Values", intake.get("values")),
        ("Constraints", intake.get("constraints")),
    ]
    lines = [f"- **{k}:** {v}" for k, v in rows if v and v.strip()]
    extra = intake.get("everything")
    if extra and extra.strip():
        lines.append(f"- **Notes:** {extra.strip()}")
    return "\n".join(lines)


def verdict_md(session: Session) -> str:
    v = session.verdict
    if not v:
        return ""
    out = ["## Verdict", "", f"### Recommendation", v.recommendation, ""]
    if v.reasoning:
        out += ["### Reasoning", v.reasoning, ""]
    if v.dissent:
        out += ["### Dissent", v.dissent, ""]
    if v.next_actions:
        out += ["### Next actions", *[f"- [ ] {a}" for a in v.next_actions], ""]
    if v.open_question:
        out += ["### The open question", f"> {v.open_question}", ""]
    return "\n".join(out)


def full_transcript_md(session: Session, *, include_intake: bool = True) -> str:
    decision = (session.intake or {}).get("one_sentence") or "Untitled decision"
    parts = [f"# Decision Court — {decision}", ""]
    if include_intake:
        parts += ["## The case", _intake_md(session.intake or {}), ""]
    parts += ["## Proceedings", ""]
    for t in session.turns:
        if t.role == Role.SYSTEM:
            continue
        parts += [f"### {ROLE_LABEL.get(t.role, t.role.value)}", t.content, ""]
    parts += [verdict_md(session)]
    parts += ["", "---", "_Decision Court is a thinking tool, not professional "
              "medical, legal, financial, or mental-health advice._"]
    return "\n".join(parts)
