import pytest
from Untouch_Wick.candle_builder import Candle
from Untouch_Wick.wick_detector import detect_wicks, WickEvent

def create_mock_candle(open_price: str, high_price: str, low_price: str, close_price: str) -> Candle:
    return Candle(
        window_start_utc='2025-12-14T21:34:00Z',
        window_end_utc='2025-12-14T21:35:00Z',
        instId='BTC-USDT-SWAP',
        exchange='OKX',
        market='perps',
        timeframe='1m',
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume='100.0',
        trade_count=10
    )

def test_detect_wicks_high_wick_only():
    candle = create_mock_candle(open_price='100', high_price='120', low_price='100', close_price='110')
    wicks = detect_wicks(candle, tickSz='0.1')

    assert len(wicks) == 1
    assert wicks[0].wick_type == 'high'
    assert wicks[0].wick_price == '120'
    assert wicks[0].wick_size == '10' # 120 - 110
    assert wicks[0].body_size == '10' # 110 - 100

def test_detect_wicks_low_wick_only():
    candle = create_mock_candle(open_price='110', high_price='110', low_price='90', close_price='100')
    wicks = detect_wicks(candle, tickSz='0.1')

    assert len(wicks) == 1
    assert wicks[0].wick_type == 'low'
    assert wicks[0].wick_price == '90'
    assert wicks[0].wick_size == '10' # 100 - 90
    assert wicks[0].body_size == '10' # 110 - 100

def test_detect_wicks_both_wicks():
    candle = create_mock_candle(open_price='100', high_price='120', low_price='90', close_price='110')
    wicks = detect_wicks(candle, tickSz='0.1')

    assert len(wicks) == 2
    types = [w.wick_type for w in wicks]
    assert 'high' in types
    assert 'low' in types

def test_detect_wicks_no_wicks():
    candle = create_mock_candle(open_price='100', high_price='110', low_price='100', close_price='110')
    wicks = detect_wicks(candle, tickSz='0.1')

    assert len(wicks) == 0
