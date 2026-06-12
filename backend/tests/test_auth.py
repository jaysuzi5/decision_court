from app.auth import sign_state, verify_state


def test_state_roundtrip():
    token = sign_state("nonce-123")
    assert verify_state(token) == "nonce-123"


def test_tampered_state_rejected():
    token = sign_state("nonce-123")
    assert verify_state(token + "x") is None
    assert verify_state("garbage") is None
