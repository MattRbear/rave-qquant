import pytest
from decimal import Decimal
from Analysis.confluence_analyzer import prices_align, find_bucket_wall_at_price, score_confluence

def test_prices_align():
    # Exactly the same
    assert prices_align(Decimal("100"), Decimal("100"), Decimal("0.5")) is True

    # Within tolerance
    assert prices_align(Decimal("100.4"), Decimal("100"), Decimal("0.5")) is True
    assert prices_align(Decimal("99.6"), Decimal("100"), Decimal("0.5")) is True

    # Outside tolerance
    assert prices_align(Decimal("100.6"), Decimal("100"), Decimal("0.5")) is False
    assert prices_align(Decimal("99.4"), Decimal("100"), Decimal("0.5")) is False

    # Zero price edge case
    assert prices_align(Decimal("100"), Decimal("0"), Decimal("0.5")) is False

def test_find_bucket_wall_at_price_empty_buckets():
    assert find_bucket_wall_at_price({}, Decimal("100"), "bid") is None
    assert find_bucket_wall_at_price({'mid_price': '0'}, Decimal("100"), "bid") is None

def test_find_bucket_wall_at_price_bid():
    buckets = {
        'mid_price': '100',
        'bands_bps': [10, 50, 100],
        'bid_notional': ['1000', '5000', '10000'],
        'imbalance': ['10%', '20%', '30%'],
        'bid_young_active': [True, False, True],
        'bid_young_age_s': [60, 120, 180]
    }

    # Target price 99.9 (distance 10 bps, falls in band 1 i.e., <= 10)
    res = find_bucket_wall_at_price(buckets, Decimal("99.9"), "bid")
    assert res is not None
    assert res['band_idx'] == 0
    assert res['notional'] == '1000'
    assert res['imbalance'] == '10%'
    assert res['young_active'] is True
    assert res['young_age_s'] == 60

    # Target price 99.5 (distance 50 bps, falls in band 2 i.e., <= 50)
    res = find_bucket_wall_at_price(buckets, Decimal("99.5"), "bid")
    assert res is not None
    assert res['band_idx'] == 1
    assert res['notional'] == '5000'
    assert res['imbalance'] == '20%'
    assert res['young_active'] is False
    assert res['young_age_s'] == 120

    # Target price 98 (distance 200 bps, outside bands)
    res = find_bucket_wall_at_price(buckets, Decimal("98"), "bid")
    assert res is None

def test_find_bucket_wall_at_price_ask():
    buckets = {
        'mid_price': '100',
        'bands_bps': [10, 50, 100],
        'ask_notional': ['1000', '5000', '10000'],
        'imbalance': ['10%', '20%', '30%'],
        'ask_young_active': [True, False, True],
        'ask_young_age_s': [60, 120, 180]
    }

    # Target price 100.1 (distance 10 bps, falls in band 1 i.e., <= 10)
    res = find_bucket_wall_at_price(buckets, Decimal("100.1"), "ask")
    assert res is not None
    assert res['band_idx'] == 0
    assert res['notional'] == '1000'
    assert res['imbalance'] == '10%'
    assert res['young_active'] is True
    assert res['young_age_s'] == 60

def test_score_confluence_base():
    wick = {
        'wick_price': '100',
        'wick_type': 'high'
    }

    res = score_confluence(wick, None, None, None, None)
    assert res['score'] == 20
    assert res['signals'] == ['WICK']
    assert res['signal_count'] == 1

def test_score_confluence_full():
    wick = {
        'wick_price': '100.1',
        'wick_type': 'high'  # Look for ask wall, negative CVD, etc.
    }

    volume = {
        'volume_tier': 'T4',
        'absorption': True
    }

    buckets = {
        'mid_price': '100',
        'bands_bps': [20, 50, 100],
        'ask_notional': ['2000000', '5000', '10000'],  # > 1M
        'imbalance': ['+0.8', '20%', '30%'],  # > 0.7
        'ask_young_active': [True, False, True],
        'ask_young_age_s': [100, 120, 180]  # < 300
    }

    cvd = {
        'cvd_delta': '-100'  # Negative for high wick
    }

    vwap = {
        'vwap_session': '100.2'  # 100.1 vs 100.2 -> distance ~0.1% < 0.5%
    }

    res = score_confluence(wick, volume, buckets, cvd, vwap)
    # Expected score:
    # Base: 20
    # Vol T4: 15
    # Absorption: 15
    # Bucket wall >1M: 15
    # Bucket imbalance >0.7: 10
    # Young wall < 300s: 10
    # CVD aligned: 10
    # VWAP confluence: 5
    # Total: 100
    assert res['score'] == 100
    assert 'WICK' in res['signals']
    assert 'VOL_T4' in res['signals']
    assert 'ABSORPTION' in res['signals']
    assert 'WALL_2.0M' in res['signals']
    assert 'IMB_0.80' in res['signals']
    assert 'YOUNG_100s' in res['signals']
    assert 'CVD_ALIGNED' in res['signals']
    assert 'VWAP_SESSION' in res['signals']

def test_score_confluence_cap():
    wick = {
        'wick_price': '100.1',
        'wick_type': 'high'
    }

    volume = {
        'volume_tier': 'T4',
        'absorption': True
    }

    buckets = {
        'mid_price': '100',
        'bands_bps': [20, 50, 100],
        'ask_notional': ['2000000', '5000', '10000'],
        'imbalance': ['+0.8', '20%', '30%'],
        'ask_young_active': [True, False, True],
        'ask_young_age_s': [100, 120, 180]
    }

    cvd = {
        'cvd_delta': '-100'
    }

    vwap = {
        'vwap_session': '100.2'
    }

    res = score_confluence(wick, volume, buckets, cvd, vwap)
    assert res['score'] <= 100
