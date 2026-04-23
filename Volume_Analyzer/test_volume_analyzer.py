import pytest
from decimal import Decimal
from datetime import datetime, timezone
from Volume_Analyzer.volume_analyzer import (
    calculate_mad,
    calculate_modified_zscore,
    detect_volume_anomaly,
    calculate_volume_tier,
    detect_absorption,
    detect_divergence,
    floor_to_minute,
    Trade,
    aggregate_minute,
)


def test_calculate_mad():
    assert calculate_mad([]) == Decimal('0')
    assert calculate_mad([Decimal('1'), Decimal('1'), Decimal('1')]) == Decimal('0')

    # odd: 1, 3, 5 -> median 3. deviations: 2, 0, 2 -> sorted: 0, 2, 2 -> median: 2
    assert calculate_mad([Decimal('1'), Decimal('3'), Decimal('5')]) == Decimal('2')

    # even: 1, 2, 3, 4 -> median 2.5. deviations: 1.5, 0.5, 0.5, 1.5 -> sorted: 0.5, 0.5, 1.5, 1.5 -> median: 1.0
    assert calculate_mad([Decimal('1'), Decimal('2'), Decimal('3'), Decimal('4')]) == Decimal('1')


def test_calculate_modified_zscore():
    # Less than 3 items should return None
    assert calculate_modified_zscore(Decimal('10'), [Decimal('1'), Decimal('2')]) is None

    # MAD is zero (all identical elements) should return None
    assert calculate_modified_zscore(Decimal('10'), [Decimal('1'), Decimal('1'), Decimal('1')]) is None

    # Example calculation
    # values: 1, 2, 3, 4, 10
    # median: 3
    # deviations: 2, 1, 0, 1, 7
    # sorted devs: 0, 1, 1, 2, 7 -> median dev (MAD): 1
    # modified z = 0.6745 * (10 - 3) / 1 = 0.6745 * 7 = 4.7215
    z = calculate_modified_zscore(Decimal('10'), [Decimal('1'), Decimal('2'), Decimal('3'), Decimal('4'), Decimal('10')])
    assert z == Decimal('4.7215')


def test_detect_volume_anomaly():
    # Not enough history
    is_anomaly, score = detect_volume_anomaly(Decimal('10'), ["1", "2"])
    assert not is_anomaly
    assert score is None

    # Normal volume
    is_anomaly, score = detect_volume_anomaly(Decimal('5'), ["1", "3", "5", "7", "9"])
    assert not is_anomaly
    assert score is not None
    assert abs(score) <= Decimal('3.5')

    # Anomaly volume (threshold 3.5)
    # median=5, mad=2, modified_z(20) = 0.6745 * (20 - 5) / 2 = 5.05875 > 3.5
    is_anomaly, score = detect_volume_anomaly(Decimal('20'), ["1", "3", "5", "7", "9"])
    assert is_anomaly
    assert score > Decimal('3.5')


def test_calculate_volume_tier():
    # Empty history
    assert calculate_volume_tier(Decimal('10'), []) == 'T2'

    # history median is 0
    assert calculate_volume_tier(Decimal('10'), ["0", "0", "0"]) == 'T2'

    # normal history: median is 10
    history = ["10", "10", "10"]
    assert calculate_volume_tier(Decimal('4'), history) == 'T1'  # 4/10 = 0.4 <= 0.5
    assert calculate_volume_tier(Decimal('6'), history) == 'T2'  # 6/10 = 0.6 <= 1.0
    assert calculate_volume_tier(Decimal('15'), history) == 'T3' # 15/10 = 1.5 <= 2.0
    assert calculate_volume_tier(Decimal('25'), history) == 'T4' # 25/10 = 2.5 > 2.0


def test_detect_absorption():
    # Empty history
    assert not detect_absorption(Decimal('0'), Decimal('100'), [])

    # Not flat enough price (threshold is 0.1)
    assert not detect_absorption(Decimal('0.15'), Decimal('100'), ["10", "10", "10"])

    # Flat price, but normal volume (threshold is 2x median)
    assert not detect_absorption(Decimal('0.05'), Decimal('15'), ["10", "10", "10"])

    # Flat price, high volume
    assert detect_absorption(Decimal('0.05'), Decimal('25'), ["10", "10", "10"])


def test_detect_divergence():
    # No price change or no delta
    assert not detect_divergence(Decimal('0'), Decimal('10'))
    assert not detect_divergence(Decimal('1'), Decimal('0'))

    # Same direction
    assert not detect_divergence(Decimal('1'), Decimal('10'))
    assert not detect_divergence(Decimal('-1'), Decimal('-10'))

    # Opposite direction (divergence)
    assert detect_divergence(Decimal('1'), Decimal('-10'))
    assert detect_divergence(Decimal('-1'), Decimal('10'))


def test_floor_to_minute():
    ts = datetime(2023, 1, 1, 12, 34, 56, 789)
    floored = floor_to_minute(ts)
    assert floored == datetime(2023, 1, 1, 12, 34, 0, 0)


def test_trade_properties():
    # Note: Trade expects string values matching okx API
    trade = Trade(
        timestamp_utc="2023-01-01T12:34:56.789Z",
        instId="BTC-USDT-SWAP",
        side="buy",
        price="50000",
        qty_contracts="2",
        ctVal="0.01"
    )

    assert trade.timestamp == datetime(2023, 1, 1, 12, 34, 56, 789000, tzinfo=timezone.utc)
    # notional = qty * ctVal * price = 2 * 0.01 * 50000 = 1000
    assert trade.notional_usd == Decimal('1000')


def test_aggregate_minute():
    # Given no trades
    assert aggregate_minute([], datetime(2023, 1, 1, 12, 34, 0, 0)) is None

    trades = [
        Trade(
            timestamp_utc="2023-01-01T12:34:01.000Z",
            instId="BTC-USDT-SWAP",
            side="buy",
            price="50000",
            qty_contracts="200",  # 200 * 0.01 * 50000 = 100000 (whale)
            ctVal="0.01"
        ),
        Trade(
            timestamp_utc="2023-01-01T12:34:02.000Z",
            instId="BTC-USDT-SWAP",
            side="sell",
            price="51000",
            qty_contracts="1",    # 1 * 0.01 * 51000 = 510
            ctVal="0.01"
        )
    ]

    minute_ts = datetime(2023, 1, 1, 12, 34, 0, 0)
    result = aggregate_minute(trades, minute_ts)

    assert result['timestamp_utc'] == "2023-01-01T12:34:00Z"
    assert result['open'] == "50000"
    assert result['close'] == "51000"
    assert result['high'] == "51000"
    assert result['low'] == "50000"

    # price change pct = (51000 - 50000) / 50000 * 100 = 2.0
    assert result['price_change_pct'] in ["2", "2.0", "2.00"]

    assert Decimal(result['total_volume']) == Decimal("100510")
    assert Decimal(result['buy_volume']) == Decimal("100000")
    assert Decimal(result['sell_volume']) == Decimal("510")

    # delta = buy - sell = 100000 - 510 = 99490
    assert Decimal(result['delta']) == Decimal("99490")

    assert Decimal(result['whale_volume']) == Decimal("100000")
    assert result['whale_count'] == 1
    assert result['trade_count'] == 2
