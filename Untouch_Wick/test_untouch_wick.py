import pytest
from decimal import Decimal
from datetime import datetime, timezone

from Untouch_Wick.untouch_wick import check_wick_touch
from Untouch_Wick.wick_detector import WickEvent
from Untouch_Wick.candle_builder import Candle

def make_wick(wick_type='high', wick_price='100.0', creation_time='2024-01-01T00:00:00Z', tol_tip_ticks=1):
    return WickEvent(
        event_id='test',
        instId='BTC',
        timeframe='1m',
        creation_time_utc=creation_time,
        window_end_utc=creation_time,
        wick_type=wick_type,
        wick_price=wick_price,
        wick_size='1.0',
        body_size='1.0',
        candle_open='90.0',
        candle_high='100.0',
        candle_low='80.0',
        candle_close='95.0',
        status='untouched',
        tol_tip_ticks=tol_tip_ticks
    )

def make_candle(open='90.0', high='110.0', low='80.0', close='105.0', window_end='2024-01-01T00:05:00Z'):
    return Candle(
        window_start_utc='2024-01-01T00:04:00Z',
        window_end_utc=window_end,
        instId='BTC',
        exchange='OKX',
        market='PERPS',
        timeframe='1m',
        open=open,
        high=high,
        low=low,
        close=close,
        volume='100',
        trade_count=10
    )

def test_check_wick_touch_no_touch():
    wick = make_wick(wick_type='high', wick_price='100.0')
    candle = make_candle(open='90.0', high='95.0', low='85.0', close='92.0')
    res = check_wick_touch(wick, candle, Decimal('0.1'))
    assert res is None

def test_check_wick_touch_wick_only():
    wick = make_wick(wick_type='high', wick_price='100.0')
    # body is 90-95, high is 105. Touches wick but body max < 100
    candle = make_candle(open='90.0', high='105.0', low='85.0', close='95.0')
    res = check_wick_touch(wick, candle, Decimal('0.1'))
    assert res is not None
    assert res['touch_by_wick'] is True
    assert res['touch_by_body'] is False
    assert res['touch_class'] == 'wick'

def test_check_wick_touch_both():
    wick = make_wick(wick_type='high', wick_price='100.0')
    # body is 95-105. High is 110.
    candle = make_candle(open='95.0', high='110.0', low='90.0', close='105.0')
    res = check_wick_touch(wick, candle, Decimal('0.1'))
    assert res is not None
    assert res['touch_by_wick'] is True
    assert res['touch_by_body'] is True
    assert res['touch_class'] == 'both'

def test_check_wick_touch_body_only():
    # If the wick_price is between the body min and max, but extremum doesn't cross the wick for some weird reason?
    # Actually, if wick_type is 'high', body min/max are <= extremum (high). So if body touches, wick also touches.
    # But let's say wick_price = 100, open=95, close=105, high=105.
    pass

def test_check_wick_touch_low_wick():
    wick = make_wick(wick_type='low', wick_price='50.0')
    candle = make_candle(open='70.0', high='80.0', low='45.0', close='60.0')
    res = check_wick_touch(wick, candle, Decimal('0.1'))
    assert res is not None
    assert res['touch_by_wick'] is True
    assert res['touch_by_body'] is False
    assert res['touch_class'] == 'wick'

def test_check_wick_touch_tip_metrics_exact():
    wick = make_wick(wick_type='high', wick_price='100.0')
    candle = make_candle(open='90.0', high='100.0', low='80.0', close='95.0')
    res = check_wick_touch(wick, candle, Decimal('0.1'))
    assert res['tip_distance_ticks'] == 0.0
    assert res['tip_exact'] is True
    assert res['tip_near'] is False
    assert res['signal_strength'] == 'EXACT'
    assert res['penetration_ticks'] == 0

def test_check_wick_touch_tip_metrics_near():
    wick = make_wick(wick_type='high', wick_price='100.0', tol_tip_ticks=1)
    candle = make_candle(open='90.0', high='100.1', low='80.0', close='95.0')
    res = check_wick_touch(wick, candle, Decimal('0.1'))
    assert res['tip_distance_ticks'] == 1.0
    assert res['tip_exact'] is False
    assert res['tip_near'] is True
    assert res['signal_strength'] == 'NEAR'
    assert res['penetration_ticks'] == 1

def test_check_wick_touch_tip_metrics_close():
    wick = make_wick(wick_type='high', wick_price='100.0', tol_tip_ticks=1)
    candle = make_candle(open='90.0', high='100.3', low='80.0', close='95.0')
    res = check_wick_touch(wick, candle, Decimal('0.1'))
    assert res['tip_distance_ticks'] == 3.0
    assert res['tip_exact'] is False
    assert res['tip_near'] is False
    assert res['signal_strength'] == 'CLOSE'
    assert res['penetration_ticks'] == 3

def test_check_wick_touch_tip_metrics_touched():
    wick = make_wick(wick_type='high', wick_price='100.0', tol_tip_ticks=1)
    candle = make_candle(open='90.0', high='100.5', low='80.0', close='95.0')
    res = check_wick_touch(wick, candle, Decimal('0.1'))
    assert res['tip_distance_ticks'] == 5.0
    assert res['tip_exact'] is False
    assert res['tip_near'] is False
    assert res['signal_strength'] == 'TOUCHED'
    assert res['penetration_ticks'] == 5

def test_check_wick_touch_no_tick_sz():
    wick = make_wick(wick_type='high', wick_price='100.0')
    candle = make_candle(open='90.0', high='105.0', low='80.0', close='95.0')

    res_none = check_wick_touch(wick, candle, None)
    assert res_none['tip_distance_ticks'] is None
    assert res_none['tip_exact'] is None
    assert res_none['signal_strength'] is None

    res_zero = check_wick_touch(wick, candle, Decimal('0'))
    assert res_zero['tip_distance_ticks'] is None
    assert res_zero['tip_exact'] is None

def test_check_wick_touch_age_calculation():
    wick = make_wick(creation_time='2024-01-01T00:00:00Z')
    candle = make_candle(window_end='2024-01-01T00:15:00Z', open='90.0', high='105.0', low='80.0', close='95.0')
    res = check_wick_touch(wick, candle, Decimal('0.1'))
    assert res['age_at_touch_minutes'] == 15
