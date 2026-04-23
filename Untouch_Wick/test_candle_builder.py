import pytest
from datetime import datetime, timezone
from decimal import Decimal
from Untouch_Wick.candle_builder import (
    Trade,
    Candle,
    floor_to_minute,
    floor_to_timeframe,
    build_1m_candles,
    rollup_candles,
    build_all_timeframes
)

def create_trade(
    timestamp_utc="2023-10-27T10:05:30.123Z",
    price="50000.5",
    qty="2"
) -> Trade:
    return Trade(
        timestamp_utc=timestamp_utc,
        exchange="okx",
        market="perps",
        instId="BTC-USDT-SWAP",
        symbol_canon="BTC-USDT-PERP",
        trade_id="12345",
        side="buy",
        price=price,
        qty_contracts=qty,
        ctVal="0.01",
        ctMult="1",
        ctType="linear"
    )

def test_trade_properties():
    trade = create_trade(timestamp_utc="2023-10-27T10:05:30.123Z", price="50000.5")

    assert trade.timestamp == datetime(2023, 10, 27, 10, 5, 30, 123000, tzinfo=timezone.utc)
    assert trade.price_decimal == Decimal("50000.5")

def test_candle_properties():
    candle = Candle(
        window_start_utc="2023-10-27T10:05:00Z",
        window_end_utc="2023-10-27T10:06:00Z",
        instId="BTC-USDT-SWAP",
        exchange="okx",
        market="perps",
        timeframe="1m",
        open="50000",
        high="50100",
        low="49900",
        close="50050",
        volume="10",
        trade_count=5
    )

    assert candle.open_decimal == Decimal("50000")
    assert candle.high_decimal == Decimal("50100")
    assert candle.low_decimal == Decimal("49900")
    assert candle.close_decimal == Decimal("50050")

def test_floor_to_minute():
    dt = datetime(2023, 10, 27, 10, 5, 30, 123000, tzinfo=timezone.utc)
    floored = floor_to_minute(dt)
    assert floored == datetime(2023, 10, 27, 10, 5, 0, tzinfo=timezone.utc)

def test_floor_to_timeframe():
    dt = datetime(2023, 10, 27, 10, 17, 30, 123000, tzinfo=timezone.utc)

    assert floor_to_timeframe(dt, '1m') == datetime(2023, 10, 27, 10, 17, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(dt, '5m') == datetime(2023, 10, 27, 10, 15, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(dt, '15m') == datetime(2023, 10, 27, 10, 15, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(dt, '1h') == datetime(2023, 10, 27, 10, 0, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(dt, '4h') == datetime(2023, 10, 27, 8, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="Unknown timeframe: 2h"):
        floor_to_timeframe(dt, '2h')

def test_build_1m_candles_empty():
    assert build_1m_candles([]) == []

def test_build_1m_candles():
    trades = [
        create_trade("2023-10-27T10:05:01Z", "50000", "1"),
        create_trade("2023-10-27T10:05:30Z", "50100", "2"),
        create_trade("2023-10-27T10:05:45Z", "49900", "3"),
        create_trade("2023-10-27T10:05:59Z", "50050", "4"),
        # Next minute
        create_trade("2023-10-27T10:06:05Z", "50060", "5"),
    ]

    candles = build_1m_candles(trades)

    assert len(candles) == 2

    # Check first minute
    c1 = candles[0]
    assert c1.window_start_utc == "2023-10-27T10:05:00Z"
    assert c1.window_end_utc == "2023-10-27T10:06:00Z"
    assert c1.open == "50000"
    assert c1.high == "50100"
    assert c1.low == "49900"
    assert c1.close == "50050"
    assert c1.volume == "10" # 1+2+3+4
    assert c1.trade_count == 4

    # Check second minute
    c2 = candles[1]
    assert c2.window_start_utc == "2023-10-27T10:06:00Z"
    assert c2.window_end_utc == "2023-10-27T10:07:00Z"
    assert c2.open == "50060"
    assert c2.high == "50060"
    assert c2.low == "50060"
    assert c2.close == "50060"
    assert c2.volume == "5"
    assert c2.trade_count == 1

def test_rollup_candles_empty():
    assert rollup_candles([], '5m') == []

def test_rollup_candles_1m_passthrough():
    candles = build_1m_candles([create_trade()])
    assert rollup_candles(candles, '1m') == candles

def test_rollup_candles_5m():
    # Create some 1m candles spanning 10:00 to 10:07
    trades = [
        create_trade("2023-10-27T10:00:01Z", "50000", "1"),
        create_trade("2023-10-27T10:01:00Z", "50100", "2"),
        create_trade("2023-10-27T10:03:00Z", "49900", "3"),
        create_trade("2023-10-27T10:04:59Z", "50050", "4"),

        # Next 5m bucket
        create_trade("2023-10-27T10:05:00Z", "50060", "5"),
        create_trade("2023-10-27T10:06:00Z", "50200", "6"),
    ]

    candles_1m = build_1m_candles(trades)
    candles_5m = rollup_candles(candles_1m, '5m')

    assert len(candles_5m) == 2

    # First 5m candle (10:00 to 10:05)
    c1 = candles_5m[0]
    assert c1.window_start_utc == "2023-10-27T10:00:00Z"
    assert c1.window_end_utc == "2023-10-27T10:05:00Z"
    assert c1.open == "50000"
    assert c1.high == "50100"
    assert c1.low == "49900"
    assert c1.close == "50050"
    assert c1.volume == "10" # 1+2+3+4
    assert c1.trade_count == 4

    # Second 5m candle (10:05 to 10:10)
    c2 = candles_5m[1]
    assert c2.window_start_utc == "2023-10-27T10:05:00Z"
    assert c2.window_end_utc == "2023-10-27T10:10:00Z"
    assert c2.open == "50060"
    assert c2.high == "50200"
    assert c2.low == "50060"
    assert c2.close == "50200"
    assert c2.volume == "11" # 5+6
    assert c2.trade_count == 2

def test_rollup_candles_invalid_timeframe():
    candles_1m = build_1m_candles([create_trade()])
    with pytest.raises(ValueError, match="Unknown timeframe: 2h"):
        rollup_candles(candles_1m, '2h')

def test_build_all_timeframes():
    trades = [
        create_trade("2023-10-27T10:00:01Z", "50000", "1"),
        create_trade("2023-10-27T10:15:01Z", "50100", "2"),
    ]

    result = build_all_timeframes(trades)

    assert set(result.keys()) == {'1m', '5m', '15m', '1h', '4h'}
    assert len(result['1m']) == 2
    assert len(result['5m']) == 2
    assert len(result['15m']) == 2
    assert len(result['1h']) == 1  # Both in 10:00-11:00
    assert len(result['4h']) == 1  # Both in 08:00-12:00

    # Check 1h aggregation
    c1h = result['1h'][0]
    assert c1h.open == "50000"
    assert c1h.high == "50100"
    assert c1h.low == "50000"
    assert c1h.close == "50100"
    assert c1h.volume == "3"

def test_build_all_timeframes_empty():
    result = build_all_timeframes([])
    assert set(result.keys()) == {'1m', '5m', '15m', '1h', '4h'}
    for k, v in result.items():
        assert v == []
