from app.orchestrator import parse_verdict

FULL = """## Recommendation
Take the job, but renegotiate the start date.

## Reasoning
The petitioner's values point toward growth. The fear is real but survivable.

## Dissent
Staying preserves stability the petitioner undervalues; the new role may not last.

## Next actions
- Call the recruiter to ask for two more weeks
- Run a 3-month family budget
- Tell your partner the real number

## Open question
Whose approval are you actually waiting for?
"""


def test_parses_all_sections():
    v = parse_verdict(FULL)
    assert v["recommendation"].startswith("Take the job")
    assert "growth" in v["reasoning"]
    assert "stability" in v["dissent"]
    assert v["next_actions"] == [
        "Call the recruiter to ask for two more weeks",
        "Run a 3-month family budget",
        "Tell your partner the real number",
    ]
    assert v["open_question"] == "Whose approval are you actually waiting for?"


def test_strips_numbered_and_starred_bullets():
    raw = (
        "## Recommendation\nDo it.\n\n## Reasoning\nBecause.\n\n## Dissent\nMaybe not.\n\n"
        "## Next actions\n1. First thing\n2) Second thing\n* Third thing\n\n"
        "## Open question\nWhat next?"
    )
    v = parse_verdict(raw)
    assert v["next_actions"] == ["First thing", "Second thing", "Third thing"]


def test_missing_sections_are_empty_not_crash():
    raw = "## Recommendation\nJust do it.\n\n## Reasoning\nClear enough."
    v = parse_verdict(raw)
    assert v["recommendation"] == "Just do it."
    assert v["reasoning"] == "Clear enough."
    assert v["dissent"] == ""
    assert v["next_actions"] == []
    assert v["open_question"] == ""


def test_unstructured_output_falls_back_to_recommendation():
    raw = "I think you should probably wait a bit before deciding."
    v = parse_verdict(raw)
    assert v["recommendation"].startswith("I think you should")
    assert v["next_actions"] == []


def test_header_match_is_case_insensitive():
    raw = "## RECOMMENDATION\nYes.\n\n## reasoning\nGood reasons."
    v = parse_verdict(raw)
    assert v["recommendation"] == "Yes."
    assert v["reasoning"] == "Good reasons."
