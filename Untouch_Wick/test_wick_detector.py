import pytest
from candle_builder import Candle
from wick_detector import detect_wicks, WickEvent

def create_candle(open_price: str, high_price: str, low_price: str, close_price: str) -> Candle:
    """Helper function to create a Candle object."""
    return Candle(
        window_start_utc="2024-01-01T00:00:00Z",
        window_end_utc="2024-01-01T00:01:00Z",
        instId="BTC-USDT-SWAP",
        exchange="OKX",
        market="PERP",
        timeframe="1m",
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume="10.0",
        trade_count=100
    )

def test_detect_wicks_both_wicks_bullish():
    # Bullish candle with both upper and lower wicks
    # O: 100, H: 120, L: 90, C: 110
    # Upper wick: 120 - 110 = 10
    # Lower wick: 100 - 90 = 10
    candle = create_candle("100", "120", "90", "110")
    wicks = detect_wicks(candle, tickSz="0.1")

    assert len(wicks) == 2

    upper_wick = next(w for w in wicks if w.wick_type == 'high')
    assert upper_wick.wick_price == "120"
    assert upper_wick.wick_size == "10"
    assert upper_wick.body_size == "10"
    assert upper_wick.status == "untouched"

    lower_wick = next(w for w in wicks if w.wick_type == 'low')
    assert lower_wick.wick_price == "90"
    assert lower_wick.wick_size == "10"
    assert lower_wick.body_size == "10"
    assert lower_wick.status == "untouched"

def test_detect_wicks_both_wicks_bearish():
    # Bearish candle with both upper and lower wicks
    # O: 110, H: 120, L: 90, C: 100
    # Upper wick: 120 - 110 = 10
    # Lower wick: 100 - 90 = 10
    candle = create_candle("110", "120", "90", "100")
    wicks = detect_wicks(candle, tickSz="0.1")

    assert len(wicks) == 2

    upper_wick = next(w for w in wicks if w.wick_type == 'high')
    assert upper_wick.wick_price == "120"
    assert upper_wick.wick_size == "10"
    assert upper_wick.body_size == "10"

    lower_wick = next(w for w in wicks if w.wick_type == 'low')
    assert lower_wick.wick_price == "90"
    assert lower_wick.wick_size == "10"
    assert lower_wick.body_size == "10"

def test_detect_wicks_only_upper_wick():
    # Bullish candle with only upper wick (Marubozu open)
    # O: 100, H: 120, L: 100, C: 110
    # Upper wick: 120 - 110 = 10
    # Lower wick: none (100 - 100 = 0)
    candle = create_candle("100", "120", "100", "110")
    wicks = detect_wicks(candle, tickSz="0.1")

    assert len(wicks) == 1
    assert wicks[0].wick_type == 'high'
    assert wicks[0].wick_price == "120"
    assert wicks[0].wick_size == "10"

def test_detect_wicks_only_lower_wick():
    # Bullish candle with only lower wick (Marubozu close)
    # O: 100, H: 110, L: 90, C: 110
    # Upper wick: none (110 - 110 = 0)
    # Lower wick: 100 - 90 = 10
    candle = create_candle("100", "110", "90", "110")
    wicks = detect_wicks(candle, tickSz="0.1")

    assert len(wicks) == 1
    assert wicks[0].wick_type == 'low'
    assert wicks[0].wick_price == "90"
    assert wicks[0].wick_size == "10"

def test_detect_wicks_no_wicks():
    # Bullish Marubozu (no wicks)
    # O: 100, H: 110, L: 100, C: 110
    candle = create_candle("100", "110", "100", "110")
    wicks = detect_wicks(candle, tickSz="0.1")

    assert len(wicks) == 0

    # Bearish Marubozu (no wicks)
    # O: 110, H: 110, L: 100, C: 100
    candle = create_candle("110", "110", "100", "100")
    wicks = detect_wicks(candle, tickSz="0.1")

    assert len(wicks) == 0

def test_detect_wicks_doji():
    # Doji (O = C), with wicks
    # O: 100, H: 110, L: 90, C: 100
    candle = create_candle("100", "110", "90", "100")
    wicks = detect_wicks(candle, tickSz="0.1")

    assert len(wicks) == 2

    upper_wick = next(w for w in wicks if w.wick_type == 'high')
    assert upper_wick.wick_price == "110"
    assert upper_wick.wick_size == "10"
    assert upper_wick.body_size == "0"

    lower_wick = next(w for w in wicks if w.wick_type == 'low')
    assert lower_wick.wick_price == "90"
    assert lower_wick.wick_size == "10"
    assert lower_wick.body_size == "0"
