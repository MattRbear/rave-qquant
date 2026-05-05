from decimal import Decimal
from Untouch_Wick.candle_builder import Candle

def test_candle_decimal_properties():
    # Instantiate a Candle with specific string values
    candle = Candle(
        window_start_utc="2023-01-01T00:00:00Z",
        window_end_utc="2023-01-01T00:01:00Z",
        instId="BTC-USDT-SWAP",
        exchange="OKX",
        market="swap",
        timeframe="1m",
        open="100.5",
        high="105.0",
        low="99.5",
        close="102.25",
        volume="10.0",
        trade_count=100
    )

    # Assert that the *_decimal properties return correct Decimal objects
    assert candle.open_decimal == Decimal("100.5")
    assert isinstance(candle.open_decimal, Decimal)

    assert candle.high_decimal == Decimal("105.0")
    assert isinstance(candle.high_decimal, Decimal)

    assert candle.low_decimal == Decimal("99.5")
    assert isinstance(candle.low_decimal, Decimal)

    assert candle.close_decimal == Decimal("102.25")
    assert isinstance(candle.close_decimal, Decimal)
