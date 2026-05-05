import pytest
from decimal import Decimal, InvalidOperation
from Untouch_Wick.candle_builder import Candle

def create_valid_candle(open="100.5", high="105.0", low="99.5", close="102.0"):
    return Candle(
        window_start_utc="2024-01-01T00:00:00Z",
        window_end_utc="2024-01-01T00:01:00Z",
        instId="BTC-USDT-SWAP",
        exchange="OKX",
        market="perps",
        timeframe="1m",
        open=open,
        high=high,
        low=low,
        close=close,
        volume="10",
        trade_count=5
    )

def test_candle_decimal_properties():
    """Test that decimal properties return correct Decimal objects."""
    candle = create_valid_candle(
        open="100.5",
        high="105.0",
        low="99.5",
        close="102.0"
    )

    assert isinstance(candle.open_decimal, Decimal)
    assert candle.open_decimal == Decimal("100.5")

    assert isinstance(candle.high_decimal, Decimal)
    assert candle.high_decimal == Decimal("105.0")

    assert isinstance(candle.low_decimal, Decimal)
    assert candle.low_decimal == Decimal("99.5")

    assert isinstance(candle.close_decimal, Decimal)
    assert candle.close_decimal == Decimal("102.0")

def test_candle_invalid_decimal():
    """Test that invalid string inputs raise decimal.InvalidOperation."""
    candle = create_valid_candle(
        open="invalid",
        high="105.0",
        low="99.5",
        close="102.0"
    )

    with pytest.raises(InvalidOperation):
        _ = candle.open_decimal

    candle = create_valid_candle(open="100.5", high="invalid")
    with pytest.raises(InvalidOperation):
        _ = candle.high_decimal

    candle = create_valid_candle(open="100.5", low="invalid")
    with pytest.raises(InvalidOperation):
        _ = candle.low_decimal

    candle = create_valid_candle(open="100.5", close="invalid")
    with pytest.raises(InvalidOperation):
        _ = candle.close_decimal
