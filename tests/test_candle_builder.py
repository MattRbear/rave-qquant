from decimal import Decimal
from Untouch_Wick.candle_builder import Candle

def test_candle_decimal_properties():
    """Test that the decimal properties of Candle return the correct Decimal objects."""
    candle = Candle(
        window_start_utc='2024-05-01T00:00:00Z',
        window_end_utc='2024-05-01T00:01:00Z',
        instId='BTC-USDT-SWAP',
        exchange='OKX',
        market='perps',
        timeframe='1m',
        open='100.5',
        high='105.0',
        low='95.5',
        close='102.0',
        volume='10.0',
        trade_count=5
    )

    assert isinstance(candle.open_decimal, Decimal)
    assert candle.open_decimal == Decimal('100.5')

    assert isinstance(candle.high_decimal, Decimal)
    assert candle.high_decimal == Decimal('105.0')

    assert isinstance(candle.low_decimal, Decimal)
    assert candle.low_decimal == Decimal('95.5')

    assert isinstance(candle.close_decimal, Decimal)
    assert candle.close_decimal == Decimal('102.0')
