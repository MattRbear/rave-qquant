import pytest
from decimal import Decimal
from datetime import datetime, timezone
from dataclasses import dataclass

from Untouch_Wick.candle_builder import Candle
from Untouch_Wick.wick_detector import WickEvent
from Untouch_Wick.untouch_wick import check_wick_touch

@pytest.fixture
def base_wick():
    return WickEvent(
        event_id="BTC-USDT-SWAP|1m|2023-01-01T00:00:00Z|high",
        instId="BTC-USDT-SWAP",
        timeframe="1m",
        creation_time_utc="2023-01-01T00:00:00Z",
        window_end_utc="2023-01-01T00:00:00Z",
        wick_type="high",
        wick_price="60000",
        wick_size="100",
        body_size="50",
        candle_open="59850",
        candle_high="60000",
        candle_low="59800",
        candle_close="59900",
        status="untouched"
    )

@pytest.fixture
def base_candle():
    return Candle(
        window_start_utc="2023-01-01T00:05:00Z",
        window_end_utc="2023-01-01T00:06:00Z",
        instId="BTC-USDT-SWAP",
        exchange="okx",
        market="perps",
        timeframe="1m",
        open="50000",
        high="50000",
        low="50000",
        close="50000",
        volume="100",
        trade_count=100
    )

def test_no_touch(base_wick, base_candle):
    base_candle.open = "50000"
    base_candle.high = "55000"
    base_candle.low = "49000"
    base_candle.close = "51000"

    result = check_wick_touch(base_wick, base_candle, Decimal('0.1'))
    assert result is None

def test_touch_by_body_only(base_wick, base_candle):
    # wick price is 60000
    base_candle.open = "59000"
    base_candle.high = "61000"
    base_candle.low = "58000"
    base_candle.close = "60500" # Body max is 60500, min is 59000. Wick is 60000.

    result = check_wick_touch(base_wick, base_candle, Decimal('0.1'))
    assert result is not None
    assert result['touch_by_body'] is True
    assert result['touch_by_wick'] is True # high wick is >= 60000
    # Wait, if body touches, then wick touches as well (since wick includes body).
    # To test body only touch is actually impossible for a normal candle where high >= body_max,
    # but check_wick_touch defines touch_by_wick as h >= wick_price (for high wick)
    # If wick is high, touch_by_wick = h >= wick_price.
    # If body touches, body_max >= wick_price, therefore h >= body_max >= wick_price,
    # so touch_by_wick is ALWAYS true if touch_by_body is true for a high wick.
    # Therefore touch_class will be 'both'.

    assert result['touch_class'] == 'both'

def test_touch_by_wick_only(base_wick, base_candle):
    # wick price is 60000 (high wick)
    base_candle.open = "59000"
    base_candle.close = "59500"
    base_candle.high = "60100"
    base_candle.low = "58000"

    # Body is [59000, 59500]. Wick_price is 60000. Body does not touch.
    # High is 60100 >= 60000. Wick touches.

    result = check_wick_touch(base_wick, base_candle, Decimal('0.1'))
    assert result is not None
    assert result['touch_by_body'] is False
    assert result['touch_by_wick'] is True
    assert result['touch_class'] == 'wick'

    # Penetration ticks: max(0, 60100 - 60000) / 0.1 = 100 / 0.1 = 1000
    assert result['penetration_ticks'] == 1000

def test_tip_exact(base_wick, base_candle):
    # wick price is 60000 (high wick)
    base_candle.open = "59000"
    base_candle.close = "59500"
    base_candle.high = "60000"
    base_candle.low = "58000"

    result = check_wick_touch(base_wick, base_candle, Decimal('0.1'))
    assert result is not None
    assert result['tip_exact'] is True
    assert result['tip_distance_ticks'] == 0
    assert result['signal_strength'] == 'EXACT'
    assert result['penetration_ticks'] == 0

def test_tip_near(base_wick, base_candle):
    # wick price is 60000 (high wick)
    # let's set high to 60000.1, tick_sz is 0.1 -> tip distance = abs(60000.1 - 60000) / 0.1 = 1
    base_candle.open = "59000"
    base_candle.close = "59500"
    base_candle.high = "60000.1"
    base_candle.low = "58000"

    result = check_wick_touch(base_wick, base_candle, Decimal('0.1'))
    assert result is not None
    assert result['tip_near'] is True
    assert result['tip_distance_ticks'] == 1
    assert result['signal_strength'] == 'NEAR'
    assert result['penetration_ticks'] == 1

def test_tip_close_and_touched(base_wick, base_candle):
    # tip distance 3 -> close
    base_candle.open = "59000"
    base_candle.close = "59500"
    base_candle.high = "60000.3"
    base_candle.low = "58000"

    result = check_wick_touch(base_wick, base_candle, Decimal('0.1'))
    assert result['tip_distance_ticks'] == 3
    assert result['signal_strength'] == 'CLOSE'
    assert result['penetration_ticks'] == 3

    # tip distance 4 -> touched
    base_candle.high = "60000.4"
    result = check_wick_touch(base_wick, base_candle, Decimal('0.1'))
    assert result['tip_distance_ticks'] == 4
    assert result['signal_strength'] == 'TOUCHED'
    assert result['penetration_ticks'] == 4

def test_null_tick_sz(base_wick, base_candle):
    base_candle.open = "59000"
    base_candle.close = "59500"
    base_candle.high = "60100"
    base_candle.low = "58000"

    result = check_wick_touch(base_wick, base_candle, None)
    assert result is not None
    assert result['touch_by_wick'] is True
    assert result['tip_distance_ticks'] is None
    assert result['tip_exact'] is None
    assert result['tip_near'] is None
    assert result['signal_strength'] is None
    assert result['penetration_ticks'] is None

def test_low_wick(base_wick, base_candle):
    base_wick.wick_type = "low"
    base_wick.wick_price = "50000"

    # Miss
    base_candle.open = "51000"
    base_candle.close = "52000"
    base_candle.low = "50500"
    base_candle.high = "53000"

    assert check_wick_touch(base_wick, base_candle, Decimal('0.1')) is None

    # Touch by wick only
    base_candle.low = "49999.9"
    result = check_wick_touch(base_wick, base_candle, Decimal('0.1'))
    assert result is not None
    assert result['touch_class'] == 'wick'
    assert result['touch_by_wick'] is True
    assert result['touch_by_body'] is False
    assert result['tip_distance_ticks'] == 1
    assert result['penetration_ticks'] == 1

    # Touch by both
    base_candle.open = "49000"
    result = check_wick_touch(base_wick, base_candle, Decimal('0.1'))
    assert result is not None
    assert result['touch_class'] == 'both'
    assert result['touch_by_wick'] is True
    assert result['touch_by_body'] is True

def test_age_at_touch_minutes(base_wick, base_candle):
    base_wick.creation_time_utc = "2023-01-01T12:00:00Z"
    base_candle.window_end_utc = "2023-01-01T12:05:00Z"

    # Setup touch
    base_candle.open = "59000"
    base_candle.close = "59500"
    base_candle.high = "60000"
    base_candle.low = "58000"

    result = check_wick_touch(base_wick, base_candle, Decimal('0.1'))
    assert result is not None
    assert result['age_at_touch_minutes'] == 5
