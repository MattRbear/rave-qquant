from datetime import datetime, timezone
from decimal import Decimal
import pytest

from Untouch_Wick.candle_builder import Trade

def create_mock_trade(timestamp_utc="2024-05-08T12:34:56.789Z", price="50000.5"):
    """Helper to create a Trade object with minimal required fields."""
    return Trade(
        timestamp_utc=timestamp_utc,
        exchange="okx",
        market="perps",
        instId="BTC-USDT-SWAP",
        symbol_canon="BTC-USDT",
        trade_id="123456789",
        side="buy",
        price=price,
        qty_contracts="1",
        ctVal="0.01",
        ctMult="1",
        ctType="linear"
    )

def test_trade_timestamp_property_with_z():
    """Test the timestamp property parses UTC strings ending in 'Z' correctly."""
    trade = create_mock_trade(timestamp_utc="2024-05-08T12:34:56.789Z")

    dt = trade.timestamp

    assert isinstance(dt, datetime)
    assert dt.year == 2024
    assert dt.month == 5
    assert dt.day == 8
    assert dt.hour == 12
    assert dt.minute == 34
    assert dt.second == 56
    assert dt.microsecond == 789000
    assert dt.tzinfo == timezone.utc

def test_trade_timestamp_property_with_offset():
    """Test the timestamp property parses valid ISO format strings without 'Z' if that occurs."""
    trade = create_mock_trade(timestamp_utc="2024-05-08T12:34:56.789+00:00")

    dt = trade.timestamp

    assert isinstance(dt, datetime)
    assert dt.year == 2024
    assert dt.tzinfo == timezone.utc

def test_trade_price_decimal_property():
    """Test the price_decimal property parses string prices correctly."""
    trade = create_mock_trade(price="50000.5")

    price_dec = trade.price_decimal

    assert isinstance(price_dec, Decimal)
    assert price_dec == Decimal("50000.5")

def test_trade_price_decimal_property_scientific():
    """Test the price_decimal property parses scientific notation."""
    trade = create_mock_trade(price="1.5e-3")

    price_dec = trade.price_decimal

    assert isinstance(price_dec, Decimal)
    assert price_dec == Decimal("0.0015")
