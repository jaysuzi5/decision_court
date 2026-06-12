from app.ratelimit import SlidingWindowLimiter


def test_allows_up_to_limit_then_blocks():
    lim = SlidingWindowLimiter(max_events=3, window_sec=60)
    assert lim.allow("ip", now=0)
    assert lim.allow("ip", now=1)
    assert lim.allow("ip", now=2)
    assert not lim.allow("ip", now=3)


def test_window_expiry_frees_capacity():
    lim = SlidingWindowLimiter(max_events=2, window_sec=60)
    assert lim.allow("ip", now=0)
    assert lim.allow("ip", now=10)
    assert not lim.allow("ip", now=20)
    # first hit (t=0) ages out of the 60s window by t=61
    assert lim.allow("ip", now=61)


def test_keys_are_independent():
    lim = SlidingWindowLimiter(max_events=1, window_sec=60)
    assert lim.allow("a", now=0)
    assert lim.allow("b", now=0)
    assert not lim.allow("a", now=1)


def test_retry_after_reports_seconds_until_oldest_expires():
    lim = SlidingWindowLimiter(max_events=1, window_sec=60)
    lim.allow("ip", now=100)
    assert lim.retry_after("ip", now=100) == 60
    assert lim.retry_after("ip", now=130) == 30
    assert lim.retry_after("unseen", now=0) == 0
