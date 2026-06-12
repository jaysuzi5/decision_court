"""Structural crisis pre-check. Runs on intake and every user reply BEFORE any
trial turn proceeds. Keep matching conservative-but-sensitive; false positives here
cost a gentle message, false negatives cost much more."""

import re

# Region-keyed crisis resources. Add regions via env CRISIS_REGION.
CRISIS_RESOURCES: dict[str, str] = {
    "US": (
        "**988 Suicide & Crisis Lifeline** — call or text **988** (24/7, free, confidential).\n"
        "**Crisis Text Line** — text **HOME** to **741741**.\n"
        "If you are in immediate danger, call **911**."
    ),
    "INTL": (
        "Find a crisis line in your country: **https://findahelpline.com**.\n"
        "If you are in immediate danger, contact your local emergency number."
    ),
}

_PATTERNS = [
    r"\bkill(ing)?\s+my\s?self\b",
    r"\bkill\s+me\b",
    r"\bend(ing)?\s+(my|it)\s+(life|all)\b",
    r"\bsuicid",
    r"\bwant\s+to\s+die\b",
    r"\bdon'?t\s+want\s+to\s+(live|be here|exist)\b",
    r"\bno\s+(reason|point)\b[^.\n]{0,15}\b(live|living|go on|be here|exist)\b",
    r"\b(take|taking)\s+my\s+(own\s+)?life\b",
    r"\bself[\s-]?harm",
    r"\bhurt(ing)?\s+my\s?self\b",
    r"\bcut(ting)?\s+my\s?self\b",
    r"\bbetter\s+off\s+(dead|without me)\b",
    r"\boverdos",
    r"\bhe\s+hits\s+me\b",
    r"\bshe\s+hits\s+me\b",
    r"\bthey\s+(hit|beat|abuse)\s+me\b",
    r"\bbeing\s+abused\b",
]
_REGEX = re.compile("|".join(_PATTERNS), re.IGNORECASE)


def resources_for(region: str) -> str:
    return CRISIS_RESOURCES.get(region.upper(), CRISIS_RESOURCES["INTL"])


def detect_crisis(text: str) -> bool:
    if not text:
        return False
    return _REGEX.search(text) is not None


def crisis_response(region: str) -> str:
    return (
        "I'm going to step out of the courtroom for a moment, because what you wrote "
        "matters more than any decision we could put on trial.\n\n"
        "It sounds like you may be carrying something very heavy right now. You deserve "
        "real support from a person, not a debate. Please reach out:\n\n"
        f"{resources_for(region)}\n\n"
        "You can come back and put your decision on trial any time. Right now, please "
        "talk to someone who can be with you in this."
    )
