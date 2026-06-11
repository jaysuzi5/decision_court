"""Persona definitions + case-file assembly. Loads the version-controlled prompt
files at startup so they can be iterated without touching code."""

from functools import lru_cache
from pathlib import Path

from .schemas import Intake

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


@lru_cache
def _load(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


def house_rules() -> str:
    return _load("house_rules.md")


PERSONA_FILES = {
    "prosecutor": "prosecutor.md",
    "defender": "defender.md",
    "judge": "judge.md",
}


def system_prompt(persona: str, *, extra: str = "") -> str:
    parts = [house_rules(), _load(PERSONA_FILES[persona])]
    if extra:
        parts.append(extra)
    return "\n\n---\n\n".join(parts)


def case_file(intake: Intake) -> str:
    """The shared, identical context block fed to all three agents each turn."""
    fields = [
        ("The decision (one sentence)", intake.one_sentence),
        ("Leaning toward", intake.leaning),
        ("Afraid of", intake.afraid_of),
        ("What matters most (values)", intake.values),
        ("Hard constraints", intake.constraints),
        ("Everything else they pasted", intake.everything),
    ]
    lines = ["## CASE FILE"]
    for label, val in fields:
        if val and val.strip():
            lines.append(f"**{label}:** {val.strip()}")
    return "\n".join(lines)
