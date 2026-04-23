import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from Untouch_Wick.candle_builder import Candle
from Untouch_Wick.wick_detector import detect_wicks, WickEvent
from Untouch_Wick.untouch_wick import check_wick_touch, check_wick_expiry

def create_mock_candle(open_price, high_price, low_price, close_price):
    return Candle(
        window_start_utc="2023-10-01T00:00:00Z",
        window_end_utc="2023-10-01T00:01:00Z",
        instId="BTC-USDT",
        exchange="Binance",
        market="spot",
        timeframe="1m",
        open=str(open_price),
        high=str(high_price),
        low=str(low_price),
        close=str(close_price),
        volume="10",
        trade_count=5
    )

def test_detect_wicks_normal():
    # Normal candle: high > max(o, c) and low < min(o, c)
    candle = create_mock_candle(100, 110, 90, 105)
    wicks = detect_wicks(candle, "1")

    assert len(wicks) == 2

    high_wick = next(w for w in wicks if w.wick_type == "high")
    assert high_wick.wick_price == "110"
    assert high_wick.wick_size == "5" # 110 - 105
    assert high_wick.body_size == "5" # 105 - 100

    low_wick = next(w for w in wicks if w.wick_type == "low")
    assert low_wick.wick_price == "90"
    assert low_wick.wick_size == "10" # 100 - 90
    assert low_wick.body_size == "5"

def test_detect_wicks_only_upper():
    # Only upper wick: low == min(o, c)
    candle = create_mock_candle(100, 110, 100, 105)
    wicks = detect_wicks(candle, "1")

    assert len(wicks) == 1

    high_wick = wicks[0]
    assert high_wick.wick_type == "high"
    assert high_wick.wick_price == "110"
    assert high_wick.wick_size == "5" # 110 - 105
    assert high_wick.body_size == "5" # 105 - 100

def test_detect_wicks_only_lower():
    # Only lower wick: high == max(o, c)
    candle = create_mock_candle(100, 105, 90, 105)
    wicks = detect_wicks(candle, "1")

    assert len(wicks) == 1

    low_wick = wicks[0]
    assert low_wick.wick_type == "low"
    assert low_wick.wick_price == "90"
    assert low_wick.wick_size == "10" # 100 - 90
    assert low_wick.body_size == "5" # 105 - 100

def test_detect_wicks_marubozu():
    # No wicks: high == max(o, c) and low == min(o, c)
    candle = create_mock_candle(100, 105, 100, 105)
    wicks = detect_wicks(candle, "1")

    assert len(wicks) == 0

def test_detect_wicks_doji():
    # Doji: open == close, with both wicks
    candle = create_mock_candle(100, 110, 90, 100)
    wicks = detect_wicks(candle, "1")

    assert len(wicks) == 2

    high_wick = next(w for w in wicks if w.wick_type == "high")
    assert high_wick.wick_price == "110"
    assert high_wick.wick_size == "10" # 110 - 100
    assert high_wick.body_size == "0"

    low_wick = next(w for w in wicks if w.wick_type == "low")
    assert low_wick.wick_price == "90"
    assert low_wick.wick_size == "10" # 100 - 90
    assert low_wick.body_size == "0"

def test_check_wick_expiry():
    # creation_time_utc: 2023-10-01T00:00:00Z
    wick = WickEvent(
        event_id="test",
        instId="BTC-USDT",
        timeframe="1m",
        creation_time_utc="2023-10-01T00:00:00Z",
        window_end_utc="2023-10-01T00:01:00Z",
        wick_type="high",
        wick_price="110",
        wick_size="5",
        body_size="5",
        candle_open="100",
        candle_high="110",
        candle_low="90",
        candle_close="105",
        status="untouched"
    )

    # Not expired at 100 hours
    as_of = datetime.fromisoformat("2023-10-05T04:00:00+00:00")
    assert not check_wick_expiry(wick, as_of, 168)

    # Expired at 168 hours
    as_of = datetime.fromisoformat("2023-10-08T00:00:00+00:00")
    assert check_wick_expiry(wick, as_of, 168)

def test_check_wick_touch_high_wick():
    wick = WickEvent(
        event_id="test",
        instId="BTC-USDT",
        timeframe="1m",
        creation_time_utc="2023-10-01T00:00:00Z",
        window_end_utc="2023-10-01T00:01:00Z",
        wick_type="high",
        wick_price="110",
        wick_size="5",
        body_size="5",
        candle_open="100",
        candle_high="110",
        candle_low="90",
        candle_close="105",
        status="untouched"
    )

    # Future candle that doesn't touch (high is 109)
    future_candle_miss = create_mock_candle(100, 109, 90, 105)
    assert check_wick_touch(wick, future_candle_miss, Decimal("1")) is None

    # Future candle that touches wick exactly (high is 110)
    future_candle_exact = create_mock_candle(100, 110, 90, 105)
    touch_data = check_wick_touch(wick, future_candle_exact, Decimal("1"))
    assert touch_data is not None
    assert touch_data["touch_by_wick"] is True
    assert touch_data["touch_by_body"] is False
    assert touch_data["tip_exact"] is True
    assert touch_data["signal_strength"] == "EXACT"

    # Future candle body touches wick (close is 110)
    future_candle_body = create_mock_candle(100, 115, 90, 110)
    touch_data = check_wick_touch(wick, future_candle_body, Decimal("1"))
    assert touch_data is not None
    assert touch_data["touch_by_body"] is True

def test_check_wick_touch_low_wick():
    wick = WickEvent(
        event_id="test2",
        instId="BTC-USDT",
        timeframe="1m",
        creation_time_utc="2023-10-01T00:00:00Z",
        window_end_utc="2023-10-01T00:01:00Z",
        wick_type="low",
        wick_price="90",
        wick_size="10",
        body_size="5",
        candle_open="100",
        candle_high="110",
        candle_low="90",
        candle_close="105",
        status="untouched"
    )

    # Future candle misses (low is 91)
    future_candle_miss = create_mock_candle(100, 110, 91, 105)
    assert check_wick_touch(wick, future_candle_miss, Decimal("1")) is None

    # Future candle touches (low is 89)
    future_candle_touch = create_mock_candle(100, 110, 89, 105)
    touch_data = check_wick_touch(wick, future_candle_touch, Decimal("1"))
    assert touch_data is not None
    assert touch_data["touch_by_wick"] is True
    assert touch_data["tip_distance_ticks"] == 1
    assert touch_data["signal_strength"] == "NEAR"
