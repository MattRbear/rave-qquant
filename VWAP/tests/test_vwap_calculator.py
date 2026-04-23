import pytest
from decimal import Decimal
from datetime import datetime, timezone

from VWAP.vwap_calculator import (
    Trade,
    SessionWindow,
    RollingWindow,
    AnchoredWindow,
    floor_to_midnight_utc,
    floor_to_minute
)

def create_mock_trade(
    timestamp_utc="2023-10-01T12:00:00Z",
    price="50000.0",
    qty_contracts="2",
    ctVal="0.01",
    trade_id="1",
    side="buy"
):
    """Helper to create a Trade object with default values."""
    return Trade(
        timestamp_utc=timestamp_utc,
        exchange="okx",
        market="perp",
        instId="BTC-USDT-SWAP",
        symbol_canon="BTC",
        trade_id=trade_id,
        side=side,
        price=price,
        qty_contracts=qty_contracts,
        ctVal=ctVal,
        ctMult="1",
        ctType="linear"
    )

def test_trade_properties():
    """Test Trade dataclass property parsing."""
    trade = create_mock_trade(
        timestamp_utc="2023-10-01T12:30:45Z",
        price="50000.5",
        qty_contracts="3",
        ctVal="0.01"
    )

    # Test timestamp
    ts = trade.timestamp
    assert isinstance(ts, datetime)
    assert ts.year == 2023
    assert ts.month == 10
    assert ts.day == 1
    assert ts.hour == 12
    assert ts.minute == 30
    assert ts.second == 45
    assert ts.tzinfo == timezone.utc

    # Test price_decimal
    assert trade.price_decimal == Decimal("50000.5")

    # Test notional: 3 * 0.01 * 50000.5 = 1500.015
    assert trade.notional == Decimal("1500.015")

def test_session_window_reset():
    """Test that SessionWindow resets at UTC midnight."""
    window = SessionWindow()

    # Add trade on Day 1
    t1 = create_mock_trade(timestamp_utc="2023-10-01T23:59:00Z", price="50000.0", qty_contracts="2", ctVal="0.01")
    window.add_trade(t1)
    assert window.get_trade_count() == 1
    assert window.current_session_date == "2023-10-01"

    # Add trade on Day 1 (same session)
    t2 = create_mock_trade(timestamp_utc="2023-10-01T23:59:59Z", price="51000.0", qty_contracts="2", ctVal="0.01")
    window.add_trade(t2)
    assert window.get_trade_count() == 2

    # Add trade on Day 2 (cross midnight, new session)
    t3 = create_mock_trade(timestamp_utc="2023-10-02T00:00:01Z", price="52000.0", qty_contracts="2", ctVal="0.01")
    window.add_trade(t3)

    # Should be 1 because the session reset
    assert window.get_trade_count() == 1
    assert window.current_session_date == "2023-10-02"

def test_session_window_vwap_calculation():
    """Test the math for Session VWAP calculation."""
    window = SessionWindow()

    # Empty window
    assert window.calculate_vwap() is None

    # Trade 1: price=50000, notional = 2 * 0.01 * 50000 = 1000
    t1 = create_mock_trade(price="50000.0", qty_contracts="2", ctVal="0.01")
    window.add_trade(t1)

    # Trade 2: price=60000, notional = 3 * 0.01 * 60000 = 1800
    t2 = create_mock_trade(price="60000.0", qty_contracts="3", ctVal="0.01")
    window.add_trade(t2)

    # VWAP = (1000*50000 + 1800*60000) / (1000 + 1800) = (50000000 + 108000000) / 2800 = 158000000 / 2800 = 56428.5714...
    vwap = window.calculate_vwap()

    expected_sum_price_vol = Decimal("50000") * Decimal("1000") + Decimal("60000") * Decimal("1800")
    expected_sum_vol = Decimal("1000") + Decimal("1800")
    expected_vwap = expected_sum_price_vol / expected_sum_vol

    assert vwap == expected_vwap

def test_rolling_window_trimming():
    """Test that RollingWindow properly trims old trades."""
    window = RollingWindow(window_minutes=60)

    # Base time: 12:00
    t1 = create_mock_trade(timestamp_utc="2023-10-01T12:00:00Z")
    t2 = create_mock_trade(timestamp_utc="2023-10-01T12:30:00Z")
    t3 = create_mock_trade(timestamp_utc="2023-10-01T13:00:00Z")

    window.add_trade(t1)
    window.add_trade(t2)
    window.add_trade(t3)

    assert window.get_trade_count() == 3

    # Trim with current time 13:00 (cutoff is 12:00)
    # Since t1 is exactly 12:00, it's NOT less than cutoff, so it stays
    current_time_1 = datetime.fromisoformat("2023-10-01T13:00:00+00:00")
    window.trim_to_window(current_time_1)
    assert window.get_trade_count() == 3

    # Trim with current time 13:00:01 (cutoff is 12:00:01)
    # t1 (12:00:00) is now less than cutoff, so it should be removed
    current_time_2 = datetime.fromisoformat("2023-10-01T13:00:01+00:00")
    window.trim_to_window(current_time_2)
    assert window.get_trade_count() == 2

def test_rolling_window_vwap_calculation():
    """Test the math for Rolling VWAP calculation."""
    window = RollingWindow(window_minutes=60)

    assert window.calculate_vwap() is None

    # Same numbers as session test to verify calculation math works the same
    t1 = create_mock_trade(price="50000.0", qty_contracts="2", ctVal="0.01")
    t2 = create_mock_trade(price="60000.0", qty_contracts="3", ctVal="0.01")

    window.add_trade(t1)
    window.add_trade(t2)

    vwap = window.calculate_vwap()

    expected_sum_price_vol = Decimal("50000") * Decimal("1000") + Decimal("60000") * Decimal("1800")
    expected_sum_vol = Decimal("1000") + Decimal("1800")
    expected_vwap = expected_sum_price_vol / expected_sum_vol

    assert vwap == expected_vwap

def test_anchored_window_behavior():
    """Test that AnchoredWindow respects the anchor time."""
    anchor = datetime.fromisoformat("2023-10-01T12:00:00+00:00")
    window = AnchoredWindow(anchor_time=anchor)

    # Trade before anchor - should be ignored
    t0 = create_mock_trade(timestamp_utc="2023-10-01T11:59:59Z")
    window.add_trade(t0)
    assert window.get_trade_count() == 0

    # Trade at anchor - should be included
    t1 = create_mock_trade(timestamp_utc="2023-10-01T12:00:00Z", price="50000.0", qty_contracts="2", ctVal="0.01")
    window.add_trade(t1)
    assert window.get_trade_count() == 1

    # Trade after anchor - should be included
    t2 = create_mock_trade(timestamp_utc="2023-10-01T12:05:00Z", price="60000.0", qty_contracts="3", ctVal="0.01")
    window.add_trade(t2)
    assert window.get_trade_count() == 2

    # Test calculation
    vwap = window.calculate_vwap()

    expected_sum_price_vol = Decimal("50000") * Decimal("1000") + Decimal("60000") * Decimal("1800")
    expected_sum_vol = Decimal("1000") + Decimal("1800")
    expected_vwap = expected_sum_price_vol / expected_sum_vol

    assert vwap == expected_vwap

    # Test set_anchor
    new_anchor = datetime.fromisoformat("2023-10-01T13:00:00+00:00")
    window.set_anchor(new_anchor)
    assert window.get_trade_count() == 0

def test_helpers():
    """Test timestamp helper functions."""
    ts = datetime.fromisoformat("2023-10-01T15:34:56.789+00:00")

    # Floor to minute
    minute_ts = floor_to_minute(ts)
    assert minute_ts.minute == 34
    assert minute_ts.second == 0
    assert minute_ts.microsecond == 0

    # Floor to midnight
    midnight_ts = floor_to_midnight_utc(ts)
    assert midnight_ts.hour == 0
    assert midnight_ts.minute == 0
    assert midnight_ts.second == 0
    assert midnight_ts.microsecond == 0
