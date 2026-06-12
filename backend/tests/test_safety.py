from app.safety import crisis_response, detect_crisis, resources_for


def test_detects_self_harm_signals():
    assert detect_crisis("honestly I want to kill myself")
    assert detect_crisis("there's no point in living anymore")
    assert detect_crisis("I keep thinking about ending it all")
    assert detect_crisis("I've been cutting myself again")


def test_detects_abuse_signals():
    assert detect_crisis("he hits me when he's angry")
    assert detect_crisis("I think I'm being abused")


def test_normal_decision_text_is_not_flagged():
    assert not detect_crisis("Should I quit my job to start a business?")
    assert not detect_crisis("I'm afraid of running out of savings")
    assert not detect_crisis("this commute is killing me slowly")  # idiom, not a signal
    assert not detect_crisis("")


def test_us_resources_present_in_response():
    msg = crisis_response("US")
    assert "988" in msg
    assert "741741" in msg


def test_unknown_region_falls_back_to_international():
    assert "findahelpline.com" in resources_for("ZZ")
