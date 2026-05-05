import pytest
from datetime import datetime
from Untouch_Wick.candle_builder import floor_to_timeframe

def test_floor_to_timeframe_1m():
    # Exactly on the minute
    dt1 = datetime(2023, 10, 27, 10, 15, 0, 0)
    assert floor_to_timeframe(dt1, '1m') == datetime(2023, 10, 27, 10, 15, 0, 0)

    # Middle of the minute
    dt2 = datetime(2023, 10, 27, 10, 15, 30, 500000)
    assert floor_to_timeframe(dt2, '1m') == datetime(2023, 10, 27, 10, 15, 0, 0)

    # End of the minute
    dt3 = datetime(2023, 10, 27, 10, 15, 59, 999999)
    assert floor_to_timeframe(dt3, '1m') == datetime(2023, 10, 27, 10, 15, 0, 0)

def test_floor_to_timeframe_5m():
    # Exactly on boundary
    dt1 = datetime(2023, 10, 27, 10, 15, 0, 0)
    assert floor_to_timeframe(dt1, '5m') == datetime(2023, 10, 27, 10, 15, 0, 0)

    # Middle of boundary
    dt2 = datetime(2023, 10, 27, 10, 17, 30, 0)
    assert floor_to_timeframe(dt2, '5m') == datetime(2023, 10, 27, 10, 15, 0, 0)

    # End of boundary
    dt3 = datetime(2023, 10, 27, 10, 19, 59, 999999)
    assert floor_to_timeframe(dt3, '5m') == datetime(2023, 10, 27, 10, 15, 0, 0)

    # Next boundary
    dt4 = datetime(2023, 10, 27, 10, 20, 0, 0)
    assert floor_to_timeframe(dt4, '5m') == datetime(2023, 10, 27, 10, 20, 0, 0)

def test_floor_to_timeframe_15m():
    # Exactly on boundary
    dt1 = datetime(2023, 10, 27, 10, 15, 0, 0)
    assert floor_to_timeframe(dt1, '15m') == datetime(2023, 10, 27, 10, 15, 0, 0)

    # Middle of boundary
    dt2 = datetime(2023, 10, 27, 10, 22, 0, 0)
    assert floor_to_timeframe(dt2, '15m') == datetime(2023, 10, 27, 10, 15, 0, 0)

    # End of boundary
    dt3 = datetime(2023, 10, 27, 10, 29, 59, 999999)
    assert floor_to_timeframe(dt3, '15m') == datetime(2023, 10, 27, 10, 15, 0, 0)

    # Next boundary
    dt4 = datetime(2023, 10, 27, 10, 30, 0, 0)
    assert floor_to_timeframe(dt4, '15m') == datetime(2023, 10, 27, 10, 30, 0, 0)

def test_floor_to_timeframe_1h():
    # Exactly on boundary
    dt1 = datetime(2023, 10, 27, 10, 0, 0, 0)
    assert floor_to_timeframe(dt1, '1h') == datetime(2023, 10, 27, 10, 0, 0, 0)

    # Middle of boundary
    dt2 = datetime(2023, 10, 27, 10, 30, 0, 0)
    assert floor_to_timeframe(dt2, '1h') == datetime(2023, 10, 27, 10, 0, 0, 0)

    # End of boundary
    dt3 = datetime(2023, 10, 27, 10, 59, 59, 999999)
    assert floor_to_timeframe(dt3, '1h') == datetime(2023, 10, 27, 10, 0, 0, 0)

    # Next boundary
    dt4 = datetime(2023, 10, 27, 11, 0, 0, 0)
    assert floor_to_timeframe(dt4, '1h') == datetime(2023, 10, 27, 11, 0, 0, 0)

def test_floor_to_timeframe_4h():
    # Exactly on boundary
    dt1 = datetime(2023, 10, 27, 8, 0, 0, 0)
    assert floor_to_timeframe(dt1, '4h') == datetime(2023, 10, 27, 8, 0, 0, 0)

    # Middle of boundary
    dt2 = datetime(2023, 10, 27, 10, 30, 0, 0)
    assert floor_to_timeframe(dt2, '4h') == datetime(2023, 10, 27, 8, 0, 0, 0)

    # End of boundary
    dt3 = datetime(2023, 10, 27, 11, 59, 59, 999999)
    assert floor_to_timeframe(dt3, '4h') == datetime(2023, 10, 27, 8, 0, 0, 0)

    # Next boundary
    dt4 = datetime(2023, 10, 27, 12, 0, 0, 0)
    assert floor_to_timeframe(dt4, '4h') == datetime(2023, 10, 27, 12, 0, 0, 0)

def test_floor_to_timeframe_invalid():
    dt1 = datetime(2023, 10, 27, 10, 15, 0, 0)
    with pytest.raises(ValueError, match="Unknown timeframe: 2h"):
        floor_to_timeframe(dt1, '2h')
