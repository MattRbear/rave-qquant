import pytest
from decimal import Decimal
from candle_builder import Candle
from wick_detector import detect_wicks, WickEvent

def test_detect_wicks_high_wick():
    """
    Test that detect_wicks correctly identifies an upper wick.
    We create a candle where high > max(open, close), but low == min(open, close).
    """
    candle = Candle(
        window_start_utc="2023-01-01T00:00:00Z",
        window_end_utc="2023-01-01T00:01:00Z",
        instId="BTC-USDT",
        exchange="OKX",
        market="PERP",
        timeframe="1m",
        open="100.0",
        high="120.0",
        low="100.0",
        close="110.0",
        volume="10.0",
        trade_count=5
    )

    # Body is from 100.0 to 110.0
    # Upper wick is from 110.0 to 120.0 (size 10.0)
    # Lower wick is 0.0 since low == min(open, close)

    wicks = detect_wicks(candle, tickSz="0.1")

    assert len(wicks) == 1

    wick = wicks[0]
    assert wick.wick_type == 'high'
    assert wick.wick_price == '120.0'
    assert wick.wick_size == '10.0'
    assert wick.body_size == '10.0'
    assert wick.status == 'untouched'
    assert wick.event_id == 'BTC-USDT|1m|2023-01-01T00:01:00Z|high'
