import pytest
from datetime import datetime
from Untouch_Wick.candle_builder import floor_to_timeframe, rollup_candles, Candle

def test_floor_to_timeframe_invalid():
    """Test that floor_to_timeframe raises ValueError for an invalid timeframe."""
    ts = datetime(2024, 1, 1, 12, 5, 30)
    with pytest.raises(ValueError, match="Unknown timeframe: 3m"):
        floor_to_timeframe(ts, '3m')

def test_rollup_candles_invalid_timeframe():
    """Test that rollup_candles raises ValueError for an invalid timeframe."""
    candle = Candle(
        window_start_utc="2024-01-01T12:00:00Z",
        window_end_utc="2024-01-01T12:01:00Z",
        instId="BTC-USDT",
        exchange="OKX",
        market="crypto",
        timeframe="1m",
        open="50000",
        high="50010",
        low="49990",
        close="50005",
        volume="10",
        trade_count=100
    )
    with pytest.raises(ValueError, match="Unknown timeframe: 3m"):
        rollup_candles([candle], '3m')
