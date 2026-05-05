import pytest
from datetime import datetime
from decimal import Decimal
from Untouch_Wick.candle_builder import (
    Trade, Candle,
    floor_to_minute, floor_to_timeframe,
    build_1m_candles, rollup_candles, build_all_timeframes
)


def test_floor_to_minute():
    """Test floor_to_minute removes seconds and microseconds."""
    ts = datetime(2023, 10, 25, 14, 30, 45, 123456)
    expected = datetime(2023, 10, 25, 14, 30, 0, 0)
    assert floor_to_minute(ts) == expected


def test_floor_to_timeframe():
    """Test floor_to_timeframe for various timeframes."""
    ts = datetime(2023, 10, 25, 14, 32, 45, 123456)

    # 1m
    assert floor_to_timeframe(ts, '1m') == datetime(2023, 10, 25, 14, 32, 0, 0)

    # 5m
    assert floor_to_timeframe(ts, '5m') == datetime(2023, 10, 25, 14, 30, 0, 0)

    # 15m
    assert floor_to_timeframe(ts, '15m') == datetime(2023, 10, 25, 14, 30, 0, 0)
    ts2 = datetime(2023, 10, 25, 14, 47, 45)
    assert floor_to_timeframe(ts2, '15m') == datetime(2023, 10, 25, 14, 45, 0, 0)

    # 1h
    assert floor_to_timeframe(ts, '1h') == datetime(2023, 10, 25, 14, 0, 0, 0)

    # 4h
    ts_4h1 = datetime(2023, 10, 25, 14, 30, 45) # falls into 12:00
    assert floor_to_timeframe(ts_4h1, '4h') == datetime(2023, 10, 25, 12, 0, 0, 0)

    ts_4h2 = datetime(2023, 10, 25, 1, 30, 45) # falls into 00:00
    assert floor_to_timeframe(ts_4h2, '4h') == datetime(2023, 10, 25, 0, 0, 0, 0)

    with pytest.raises(ValueError, match="Unknown timeframe: 2h"):
        floor_to_timeframe(ts, '2h')


def create_mock_trade(timestamp_utc, price, qty_contracts, side='buy'):
    return Trade(
        timestamp_utc=timestamp_utc,
        exchange="okx",
        market="swap",
        instId="BTC-USDT-SWAP",
        symbol_canon="BTC",
        trade_id="123",
        side=side,
        price=str(price),
        qty_contracts=str(qty_contracts),
        ctVal="0.01",
        ctMult="1",
        ctType="linear"
    )

def test_build_1m_candles():
    """Test build_1m_candles with trades in same and different minutes."""
    trades = [
        create_mock_trade("2023-10-25T14:30:10Z", "30000.5", "10"),
        create_mock_trade("2023-10-25T14:30:20Z", "30005.0", "5"),
        create_mock_trade("2023-10-25T14:30:30Z", "29990.0", "20"),
        create_mock_trade("2023-10-25T14:30:50Z", "30001.0", "15"), # close

        create_mock_trade("2023-10-25T14:31:05Z", "30002.0", "50"),
    ]

    candles = build_1m_candles(trades)

    assert len(candles) == 2

    c1 = candles[0]
    assert c1.window_start_utc == "2023-10-25T14:30:00Z"
    assert c1.window_end_utc == "2023-10-25T14:31:00Z"
    assert c1.open == "30000.5"
    assert c1.high == "30005.0"
    assert c1.low == "29990.0"
    assert c1.close == "30001.0"
    assert c1.volume == "50"
    assert c1.trade_count == 4

    c2 = candles[1]
    assert c2.window_start_utc == "2023-10-25T14:31:00Z"
    assert c2.window_end_utc == "2023-10-25T14:32:00Z"
    assert c2.open == "30002.0"
    assert c2.high == "30002.0"
    assert c2.low == "30002.0"
    assert c2.close == "30002.0"
    assert c2.volume == "50"
    assert c2.trade_count == 1

def test_build_1m_candles_empty():
    assert build_1m_candles([]) == []

def test_rollup_candles():
    """Test rollup_candles rolls up 1m candles into 5m accurately."""
    trades = [
        create_mock_trade("2023-10-25T14:30:10Z", "30000", "10"), # min 30
        create_mock_trade("2023-10-25T14:31:10Z", "30100", "10"), # min 31, high
        create_mock_trade("2023-10-25T14:33:10Z", "29000", "10"), # min 33, low
        create_mock_trade("2023-10-25T14:34:50Z", "29500", "10"), # min 34, close

        create_mock_trade("2023-10-25T14:35:10Z", "29600", "10"), # next 5m window
    ]

    candles_1m = build_1m_candles(trades)

    candles_5m = rollup_candles(candles_1m, '5m')

    assert len(candles_5m) == 2

    c1 = candles_5m[0]
    assert c1.window_start_utc == "2023-10-25T14:30:00Z"
    assert c1.window_end_utc == "2023-10-25T14:35:00Z"
    assert c1.open == "30000"
    assert c1.high == "30100"
    assert c1.low == "29000"
    assert c1.close == "29500"
    assert c1.volume == "40"
    assert c1.trade_count == 4

    c2 = candles_5m[1]
    assert c2.window_start_utc == "2023-10-25T14:35:00Z"
    assert c2.window_end_utc == "2023-10-25T14:40:00Z"
    assert c2.open == "29600"
    assert c2.high == "29600"
    assert c2.low == "29600"
    assert c2.close == "29600"
    assert c2.volume == "10"
    assert c2.trade_count == 1

def test_rollup_candles_empty():
    assert rollup_candles([], '5m') == []

def test_rollup_candles_unknown_timeframe():
    trades = [create_mock_trade("2023-10-25T14:30:10Z", "30000", "10")]
    candles_1m = build_1m_candles(trades)
    with pytest.raises(ValueError, match="Unknown timeframe: 2h"):
        rollup_candles(candles_1m, '2h')

def test_build_all_timeframes():
    """Test build_all_timeframes generates all expected timeframes."""
    trades = [
        create_mock_trade("2023-10-25T14:30:10Z", "30000", "10"),
    ]

    all_tf = build_all_timeframes(trades)

    assert set(all_tf.keys()) == {'1m', '5m', '15m', '1h', '4h'}

    for tf, candles in all_tf.items():
        assert len(candles) == 1
        assert candles[0].timeframe == tf

def test_build_all_timeframes_empty():
    all_tf = build_all_timeframes([])
    assert set(all_tf.keys()) == {'1m', '5m', '15m', '1h', '4h'}
    for tf, candles in all_tf.items():
        assert len(candles) == 0
