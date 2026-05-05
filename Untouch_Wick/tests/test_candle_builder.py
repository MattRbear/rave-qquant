from datetime import datetime, timezone
import pytest

from Untouch_Wick.candle_builder import floor_to_timeframe


def test_floor_to_timeframe_1m():
    # 2023-01-01 12:34:56.789012
    ts = datetime(2023, 1, 1, 12, 34, 56, 789012, tzinfo=timezone.utc)
    expected = datetime(2023, 1, 1, 12, 34, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(ts, '1m') == expected

    # Already on boundary
    ts_boundary = datetime(2023, 1, 1, 12, 34, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(ts_boundary, '1m') == ts_boundary


def test_floor_to_timeframe_5m():
    # 12:34 -> 12:30
    ts1 = datetime(2023, 1, 1, 12, 34, 56, tzinfo=timezone.utc)
    expected1 = datetime(2023, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(ts1, '5m') == expected1

    # 12:36 -> 12:35
    ts2 = datetime(2023, 1, 1, 12, 36, 12, tzinfo=timezone.utc)
    expected2 = datetime(2023, 1, 1, 12, 35, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(ts2, '5m') == expected2

    # Boundary
    ts3 = datetime(2023, 1, 1, 12, 35, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(ts3, '5m') == ts3


def test_floor_to_timeframe_15m():
    # 12:14 -> 12:00
    ts1 = datetime(2023, 1, 1, 12, 14, 59, tzinfo=timezone.utc)
    expected1 = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(ts1, '15m') == expected1

    # 12:29 -> 12:15
    ts2 = datetime(2023, 1, 1, 12, 29, 0, tzinfo=timezone.utc)
    expected2 = datetime(2023, 1, 1, 12, 15, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(ts2, '15m') == expected2

    # 12:31 -> 12:30
    ts3 = datetime(2023, 1, 1, 12, 31, 0, tzinfo=timezone.utc)
    expected3 = datetime(2023, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(ts3, '15m') == expected3

    # 12:59 -> 12:45
    ts4 = datetime(2023, 1, 1, 12, 59, 59, tzinfo=timezone.utc)
    expected4 = datetime(2023, 1, 1, 12, 45, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(ts4, '15m') == expected4

    # Boundary
    ts5 = datetime(2023, 1, 1, 12, 45, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(ts5, '15m') == ts5


def test_floor_to_timeframe_1h():
    # 12:34 -> 12:00
    ts = datetime(2023, 1, 1, 12, 34, 56, tzinfo=timezone.utc)
    expected = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(ts, '1h') == expected

    # Boundary
    ts_boundary = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(ts_boundary, '1h') == ts_boundary


def test_floor_to_timeframe_4h():
    # 03:59 -> 00:00
    ts1 = datetime(2023, 1, 1, 3, 59, 59, tzinfo=timezone.utc)
    expected1 = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(ts1, '4h') == expected1

    # 05:30 -> 04:00
    ts2 = datetime(2023, 1, 1, 5, 30, 0, tzinfo=timezone.utc)
    expected2 = datetime(2023, 1, 1, 4, 0, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(ts2, '4h') == expected2

    # 11:15 -> 08:00
    ts3 = datetime(2023, 1, 1, 11, 15, 0, tzinfo=timezone.utc)
    expected3 = datetime(2023, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(ts3, '4h') == expected3

    # 15:45 -> 12:00
    ts4 = datetime(2023, 1, 1, 15, 45, 0, tzinfo=timezone.utc)
    expected4 = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(ts4, '4h') == expected4

    # Boundary
    ts5 = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert floor_to_timeframe(ts5, '4h') == ts5


def test_floor_to_timeframe_invalid():
    ts = datetime(2023, 1, 1, 12, 34, 56, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="Unknown timeframe: 2h"):
        floor_to_timeframe(ts, '2h')
