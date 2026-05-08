import pytest
from datetime import datetime, timezone, timedelta
from untouch_wick import check_wick_expiry
from wick_detector import WickEvent

def create_mock_wick_event(creation_time: datetime) -> WickEvent:
    # Fill in all required fields with dummy data, except for creation_time_utc
    return WickEvent(
        event_id="dummy_id",
        instId="BTC-USDT",
        timeframe="1h",
        creation_time_utc=creation_time.isoformat(),
        window_end_utc=creation_time.isoformat(),
        wick_type="high",
        wick_price="50000",
        wick_size="100",
        body_size="200",
        candle_open="49000",
        candle_high="50100",
        candle_low="48000",
        candle_close="49200",
        status="untouched"
    )

def test_check_wick_expiry():
    now = datetime.now(timezone.utc)

    # Test 1: Wick is exactly on the expiry boundary (168 hours)
    # The actual code (per task description) uses strict inequality (>),
    # so an exact boundary should evaluate to False.
    wick_boundary = create_mock_wick_event(now - timedelta(hours=168))
    assert check_wick_expiry(wick_boundary, now) == False

    # Test 2: Wick is older than expiry
    wick_older = create_mock_wick_event(now - timedelta(hours=168, seconds=1))
    assert check_wick_expiry(wick_older, now) == True

    # Test 3: Wick is newer than expiry
    wick_newer = create_mock_wick_event(now - timedelta(hours=167, minutes=59))
    assert check_wick_expiry(wick_newer, now) == False

    # Test 4: Custom expiry hours boundary
    wick_custom = create_mock_wick_event(now - timedelta(hours=24))
    assert check_wick_expiry(wick_custom, now, expiry_hours=24) == False

    wick_custom_older = create_mock_wick_event(now - timedelta(hours=24, seconds=1))
    assert check_wick_expiry(wick_custom_older, now, expiry_hours=24) == True
