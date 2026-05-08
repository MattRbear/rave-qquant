import pytest
from decimal import Decimal
from datetime import datetime
from Untouch_Wick.untouch_wick import check_wick_touch
from Untouch_Wick.wick_detector import WickEvent
from Untouch_Wick.candle_builder import Candle

def create_mock_wick(wick_type='high', wick_price='100.0', creation_time_utc='2023-01-01T12:00:00Z', tol_tip_ticks=1):
    return WickEvent(
        event_id='test_event',
        instId='BTC-USDT-SWAP',
        timeframe='1m',
        creation_time_utc=creation_time_utc,
        window_end_utc=creation_time_utc,
        wick_type=wick_type,
        wick_price=wick_price,
        wick_size='1.0',
        body_size='5.0',
        candle_open='95.0',
        candle_high='100.0',
        candle_low='90.0',
        candle_close='98.0',
        status='untouched',
        tickSz='0.1',
        tol_tip_ticks=tol_tip_ticks
    )

def create_mock_candle(open='98.0', high='105.0', low='95.0', close='100.0', window_end_utc='2023-01-01T12:05:00Z'):
    return Candle(
        instId='BTC-USDT-SWAP',
        exchange='OKX',
        market='SWAP',
        timeframe='1m',
        window_start_utc='2023-01-01T12:04:00Z',
        window_end_utc=window_end_utc,
        open=open,
        high=high,
        low=low,
        close=close,
        volume='100',
        trade_count=50
    )

def test_check_wick_touch_no_touch():
    wick = create_mock_wick(wick_type='high', wick_price='100.0')
    candle = create_mock_candle(open='90.0', high='99.0', low='85.0', close='95.0')
    result = check_wick_touch(wick, candle, tick_sz=Decimal('0.1'))
    assert result is None

def test_check_wick_touch_by_wick_only():
    wick = create_mock_wick(wick_type='high', wick_price='100.0')
    # body is 90-95, high is 101 -> body doesn't touch, wick does
    candle = create_mock_candle(open='90.0', high='101.0', low='85.0', close='95.0')
    result = check_wick_touch(wick, candle, tick_sz=Decimal('0.1'))

    assert result is not None
    assert result['touch_by_wick'] is True
    assert result['touch_by_body'] is False
    assert result['touch_class'] == 'wick'

def test_check_wick_touch_by_body_only():
    # Lower wick case, wick is 90.0
    wick = create_mock_wick(wick_type='low', wick_price='90.0')
    # Body engulfs 90.0 (open=95, close=85)
    candle = create_mock_candle(open='95.0', high='95.0', low='85.0', close='85.0')
    result = check_wick_touch(wick, candle, tick_sz=Decimal('0.1'))

    assert result is not None
    assert result['touch_by_body'] is True
    assert result['touch_by_wick'] is True # l=85 <= 90 is True! So both.
    assert result['touch_class'] == 'both'

def test_check_wick_touch_signal_strength_exact():
    wick = create_mock_wick(wick_type='high', wick_price='100.0')
    candle = create_mock_candle(open='90.0', high='100.0', low='85.0', close='95.0')
    result = check_wick_touch(wick, candle, tick_sz=Decimal('0.1'))

    assert result['signal_strength'] == 'EXACT'
    assert result['tip_distance_ticks'] == 0.0
    assert result['tip_exact'] is True

def test_check_wick_touch_signal_strength_near():
    wick = create_mock_wick(wick_type='high', wick_price='100.0', tol_tip_ticks=1)
    candle = create_mock_candle(open='90.0', high='100.1', low='85.0', close='95.0')
    result = check_wick_touch(wick, candle, tick_sz=Decimal('0.1'))

    assert result['signal_strength'] == 'NEAR'
    assert result['tip_distance_ticks'] == 1.0
    assert result['tip_near'] is True

def test_check_wick_touch_signal_strength_close():
    wick = create_mock_wick(wick_type='high', wick_price='100.0')
    candle = create_mock_candle(open='90.0', high='100.3', low='85.0', close='95.0')
    result = check_wick_touch(wick, candle, tick_sz=Decimal('0.1'))

    assert result['signal_strength'] == 'CLOSE'
    assert result['tip_distance_ticks'] == 3.0

def test_check_wick_touch_signal_strength_touched():
    wick = create_mock_wick(wick_type='high', wick_price='100.0')
    candle = create_mock_candle(open='90.0', high='100.4', low='85.0', close='95.0')
    result = check_wick_touch(wick, candle, tick_sz=Decimal('0.1'))

    assert result['signal_strength'] == 'TOUCHED'
    assert result['tip_distance_ticks'] == 4.0

def test_check_wick_touch_penetration_ticks_high():
    wick = create_mock_wick(wick_type='high', wick_price='100.0')
    candle = create_mock_candle(open='90.0', high='100.5', low='85.0', close='95.0')
    result = check_wick_touch(wick, candle, tick_sz=Decimal('0.1'))

    # 100.5 - 100.0 = 0.5 / 0.1 = 5
    assert result['penetration_ticks'] == 5

def test_check_wick_touch_penetration_ticks_low():
    wick = create_mock_wick(wick_type='low', wick_price='90.0')
    candle = create_mock_candle(open='95.0', high='100.0', low='89.5', close='98.0')
    result = check_wick_touch(wick, candle, tick_sz=Decimal('0.1'))

    # 90.0 - 89.5 = 0.5 / 0.1 = 5
    assert result['penetration_ticks'] == 5

def test_check_wick_touch_age_at_touch():
    wick = create_mock_wick(wick_type='high', wick_price='100.0', creation_time_utc='2023-01-01T12:00:00Z')
    candle = create_mock_candle(open='90.0', high='100.0', low='85.0', close='95.0', window_end_utc='2023-01-01T12:05:00Z')
    result = check_wick_touch(wick, candle, tick_sz=Decimal('0.1'))

    assert result['age_at_touch_minutes'] == 5

def test_check_wick_touch_missing_tick_sz():
    wick = create_mock_wick(wick_type='high', wick_price='100.0')
    candle = create_mock_candle(open='90.0', high='101.0', low='85.0', close='95.0')
    result = check_wick_touch(wick, candle, tick_sz=None)

    assert result['touch_class'] == 'wick'
    assert result['tip_distance_ticks'] is None
    assert result['tip_exact'] is None
    assert result['tip_near'] is None
    assert result['signal_strength'] is None
    assert result['penetration_ticks'] is None
