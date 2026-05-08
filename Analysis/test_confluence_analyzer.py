import pytest
from decimal import Decimal
from Analysis.confluence_analyzer import prices_align, find_bucket_wall_at_price, score_confluence

def test_prices_align():
    tolerance = Decimal('0.5')
    # Exact match
    assert prices_align(Decimal('100'), Decimal('100'), tolerance) is True

    # Within tolerance (0.4% difference)
    assert prices_align(Decimal('100.4'), Decimal('100'), tolerance) is True
    assert prices_align(Decimal('99.6'), Decimal('100'), tolerance) is True

    # Just outside tolerance (0.6% difference)
    assert prices_align(Decimal('100.6'), Decimal('100'), tolerance) is False
    assert prices_align(Decimal('99.4'), Decimal('100'), tolerance) is False

    # Edge case: price2 = 0
    assert prices_align(Decimal('100'), Decimal('0'), tolerance) is False


def test_find_bucket_wall_at_price():
    buckets = {
        'mid_price': '10000',
        'bands_bps': [10, 50, 100],
        'bid_notional': ['1000', '2000', '3000'],
        'ask_notional': ['1500', '2500', '3500'],
        'imbalance': ['0.1', '-0.2', '0.3'],
        'bid_young_active': [True, False, False],
        'bid_young_age_s': [120, None, None],
        'ask_young_active': [False, True, False],
        'ask_young_age_s': [None, 200, None]
    }

    # Test bid side (target distance: ~5bps) - should hit band 0 (<= 10bps)
    wall = find_bucket_wall_at_price(buckets, Decimal('9995'), 'bid')
    assert wall is not None
    assert wall['band_idx'] == 0
    assert wall['notional'] == '1000'
    assert wall['young_active'] is True
    assert wall['young_age_s'] == 120

    # Test ask side (target distance: ~40bps) - should hit band 1 (<= 50bps)
    wall = find_bucket_wall_at_price(buckets, Decimal('10040'), 'ask')
    assert wall is not None
    assert wall['band_idx'] == 1
    assert wall['notional'] == '2500'
    assert wall['young_active'] is True
    assert wall['young_age_s'] == 200

    # Test outside all bands (target distance: > 100bps)
    wall = find_bucket_wall_at_price(buckets, Decimal('10200'), 'ask')
    assert wall is None

    # Test empty buckets
    assert find_bucket_wall_at_price({}, Decimal('10000'), 'bid') is None

    # Test mid_price = 0
    bad_buckets = buckets.copy()
    bad_buckets['mid_price'] = '0'
    assert find_bucket_wall_at_price(bad_buckets, Decimal('10000'), 'bid') is None


def test_score_confluence_base():
    wick = {'wick_price': '10000', 'wick_type': 'high'}
    res = score_confluence(wick, None, None, None, None)
    assert res['score'] == 20
    assert res['signals'] == ['WICK']
    assert res['signal_count'] == 1

def test_score_confluence_volume():
    wick = {'wick_price': '10000', 'wick_type': 'high'}
    volume = {'volume_tier': 'T4', 'absorption': True}
    res = score_confluence(wick, volume, None, None, None)
    assert res['score'] == 20 + 15 + 15
    assert 'VOL_T4' in res['signals']
    assert 'ABSORPTION' in res['signals']

def test_score_confluence_buckets():
    wick = {'wick_price': '10005', 'wick_type': 'high'} # 'ask' wall logic
    buckets = {
        'mid_price': '10000',
        'bands_bps': [10],
        'ask_notional': ['2000000'], # > 1M
        'imbalance': ['-0.8%'], # > 0.7
        'ask_young_active': [True],
        'ask_young_age_s': [250] # < 300
    }
    res = score_confluence(wick, None, buckets, None, None)
    # Wick (20) + Wall >1M (15) + Imb >0.7 (10) + Young (10) = 55
    assert res['score'] == 55
    assert 'WALL_2.0M' in res['signals']
    assert 'IMB_0.80' in res['signals']
    assert 'YOUNG_250s' in res['signals']

def test_score_confluence_cvd():
    wick_high = {'wick_price': '10000', 'wick_type': 'high'}
    wick_low = {'wick_price': '10000', 'wick_type': 'low'}

    # High wick aligned (negative delta)
    cvd_aligned_high = {'cvd_delta': '-500'}
    res = score_confluence(wick_high, None, None, cvd_aligned_high, None)
    assert res['score'] == 30 # Base (20) + CVD (10)
    assert 'CVD_ALIGNED' in res['signals']

    # Low wick aligned (positive delta)
    cvd_aligned_low = {'cvd_delta': '500'}
    res = score_confluence(wick_low, None, None, cvd_aligned_low, None)
    assert res['score'] == 30
    assert 'CVD_ALIGNED' in res['signals']

    # Non-aligned CVD
    cvd_unaligned_high = {'cvd_delta': '500'}
    res = score_confluence(wick_high, None, None, cvd_unaligned_high, None)
    assert res['score'] == 20 # Base only

def test_score_confluence_vwap():
    wick = {'wick_price': '10000', 'wick_type': 'high'}

    # Confluent VWAP (within 0.5% default tolerance in score_confluence)
    vwap_confluent = {'vwap_session': '10020'} # ~0.2% difference
    res = score_confluence(wick, None, None, None, vwap_confluent)
    assert res['score'] == 25 # Base (20) + VWAP (5)
    assert 'VWAP_SESSION' in res['signals']

    # Non-confluent VWAP
    vwap_unaligned = {'vwap_session': '10100'} # 1% difference
    res = score_confluence(wick, None, None, None, vwap_unaligned)
    assert res['score'] == 20 # Base only

def test_score_confluence_max_cap():
    wick = {'wick_price': '10005', 'wick_type': 'high'}
    volume = {'volume_tier': 'T4', 'absorption': True} # 15 + 15
    buckets = {
        'mid_price': '10000',
        'bands_bps': [10],
        'ask_notional': ['2000000'], # 15
        'imbalance': ['-0.8%'], # 10
        'ask_young_active': [True],
        'ask_young_age_s': [250] # 10
    }
    cvd = {'cvd_delta': '-500'} # 10
    vwap = {'vwap_session': '10000'} # 5

    # Total theoretical score: 20(base) + 30(vol) + 35(buckets) + 10(cvd) + 5(vwap) = 100
    # Let's add something extra or just check if it caps properly if it somehow goes over
    # (Actually max theoretical is exactly 100 based on these increments)

    res = score_confluence(wick, volume, buckets, cvd, vwap)
    assert res['score'] == 100
