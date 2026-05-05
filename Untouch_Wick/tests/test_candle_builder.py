import pytest
from decimal import Decimal
from Untouch_Wick.candle_builder import Candle

def test_candle_decimal_properties():
    """Test that Candle properties correctly return Decimal objects for float strings."""
    candle = Candle(
        window_start_utc="2024-01-01T00:00:00Z",
        window_end_utc="2024-01-01T00:01:00Z",
        instId="BTC-USDT-SWAP",
        exchange="OKX",
        market="perps",
        timeframe="1m",
        open="42000.5",
        high="42100.0",
        low="41900.25",
        close="42050.75",
        volume="10.5",
        trade_count=100
    )

    assert isinstance(candle.open_decimal, Decimal)
    assert candle.open_decimal == Decimal("42000.5")

    assert isinstance(candle.high_decimal, Decimal)
    assert candle.high_decimal == Decimal("42100.0")

    assert isinstance(candle.low_decimal, Decimal)
    assert candle.low_decimal == Decimal("41900.25")

    assert isinstance(candle.close_decimal, Decimal)
    assert candle.close_decimal == Decimal("42050.75")

def test_candle_decimal_properties_integers():
    """Test that Candle properties correctly return Decimal objects for integer strings."""
    candle = Candle(
        window_start_utc="2024-01-01T00:00:00Z",
        window_end_utc="2024-01-01T00:01:00Z",
        instId="BTC-USDT-SWAP",
        exchange="OKX",
        market="perps",
        timeframe="1m",
        open="42000",
        high="42100",
        low="41900",
        close="42050",
        volume="10",
        trade_count=100
    )

    assert candle.open_decimal == Decimal("42000")
    assert candle.high_decimal == Decimal("42100")
    assert candle.low_decimal == Decimal("41900")
    assert candle.close_decimal == Decimal("42050")

def test_candle_decimal_properties_scientific_notation():
    """Test that Candle properties correctly handle scientific notation."""
    candle = Candle(
        window_start_utc="2024-01-01T00:00:00Z",
        window_end_utc="2024-01-01T00:01:00Z",
        instId="PEPE-USDT-SWAP",
        exchange="OKX",
        market="perps",
        timeframe="1m",
        open="1.2e-5",
        high="1.5e-5",
        low="1.0e-5",
        close="1.3e-5",
        volume="1000000",
        trade_count=100
    )

    assert candle.open_decimal == Decimal("0.000012")
    assert candle.high_decimal == Decimal("0.000015")
    assert candle.low_decimal == Decimal("0.000010")
    assert candle.close_decimal == Decimal("0.000013")
