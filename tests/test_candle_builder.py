import pytest
from decimal import Decimal, InvalidOperation
from Untouch_Wick.candle_builder import Candle

def test_candle_decimal_properties_valid():
    """Test that valid decimal strings are correctly converted to Decimal objects."""
    candle = Candle(
        window_start_utc="2024-01-01T00:00:00Z",
        window_end_utc="2024-01-01T00:01:00Z",
        instId="BTC-USDT-SWAP",
        exchange="okx",
        market="perps",
        timeframe="1m",
        open="50000.5",
        high="50100.75",
        low="49900.25",
        close="50050.0",
        volume="10.5",
        trade_count=100
    )

    assert candle.open_decimal == Decimal("50000.5")
    assert candle.high_decimal == Decimal("50100.75")
    assert candle.low_decimal == Decimal("49900.25")
    assert candle.close_decimal == Decimal("50050.0")

def test_candle_decimal_properties_invalid():
    """Test that invalid strings raise InvalidOperation."""
    candle = Candle(
        window_start_utc="2024-01-01T00:00:00Z",
        window_end_utc="2024-01-01T00:01:00Z",
        instId="BTC-USDT-SWAP",
        exchange="okx",
        market="perps",
        timeframe="1m",
        open="invalid_open",
        high="invalid_high",
        low="invalid_low",
        close="invalid_close",
        volume="10.5",
        trade_count=100
    )

    with pytest.raises(InvalidOperation):
        _ = candle.open_decimal

    with pytest.raises(InvalidOperation):
        _ = candle.high_decimal

    with pytest.raises(InvalidOperation):
        _ = candle.low_decimal

    with pytest.raises(InvalidOperation):
        _ = candle.close_decimal
