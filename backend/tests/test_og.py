from app.og import render_card


def test_renders_png_bytes():
    png = render_card("Should I quit my job?", "Take the job, but renegotiate the start date.")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(png) > 1000


def test_handles_empty_inputs():
    png = render_card("", "")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
