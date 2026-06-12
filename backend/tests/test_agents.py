from app.agents import case_file, house_rules, system_prompt
from app.schemas import Intake


def test_system_prompt_includes_house_rules_and_persona():
    p = system_prompt("prosecutor")
    assert house_rules() in p
    # persona-specific language
    assert "Prosecutor" in p
    assert "petitioner" in p.lower()


def test_judge_extra_mode_is_appended():
    p = system_prompt("judge", extra="Mode: VERDICT")
    assert "Mode: VERDICT" in p


def test_case_file_includes_filled_fields_only():
    intake = Intake(one_sentence="Quit my job?", leaning="Yes", values="autonomy")
    cf = case_file(intake)
    assert "Quit my job?" in cf
    assert "autonomy" in cf
    # empty fields produce no label
    assert "Afraid of" not in cf
    assert "Hard constraints" not in cf


def test_case_file_has_header():
    assert case_file(Intake(one_sentence="x")).startswith("## CASE FILE")
