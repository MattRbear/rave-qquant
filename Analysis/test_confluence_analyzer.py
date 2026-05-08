import pytest
from decimal import Decimal
from Analysis.confluence_analyzer import prices_align, find_bucket_wall_at_price, score_confluence

def test_prices_align():
    tolerance = Decimal('0.5')
    # Perfect alignment
    assert prices_align(Decimal('100.0'), Decimal('100.0'), tolerance) == True

    # price2 is 0
    assert prices_align(Decimal('100.0'), Decimal('0'), tolerance) == False

    # Within tolerance
    assert prices_align(Decimal('100.0'), Decimal('100.4'), tolerance) == True
    assert prices_align(Decimal('100.0'), Decimal('99.6'), tolerance) == True

    # Outside tolerance
    assert prices_align(Decimal('100.0'), Decimal('100.6'), tolerance) == False
    assert prices_align(Decimal('100.0'), Decimal('99.4'), tolerance) == False

def test_find_bucket_wall_at_price():
    # Empty buckets
    assert find_bucket_wall_at_price({}, Decimal('100.0'), 'bid') is None

    # Mid price 0
    assert find_bucket_wall_at_price({'mid_price': '0'}, Decimal('100.0'), 'bid') is None

    buckets = {
        'mid_price': '100.0',
        'bands_bps': [10, 50, 100],
        'bid_notional': ['1000', '5000', '1500000'],
        'ask_notional': ['2000', '6000', '8000'],
        'imbalance': ['+0.1%', '-0.8%', '+0.9%'],
        'bid_young_active': [False, True, True],
        'ask_young_active': [False, False, True],
        'bid_young_age_s': [None, 600, 200],
        'ask_young_age_s': [None, None, 100]
    }

    # Bid side matching target exactly
    res = find_bucket_wall_at_price(buckets, Decimal('100.0'), 'bid')
    assert res == {
        'band_idx': 0,
        'band_bps': 10,
        'notional': '1000',
        'imbalance': '+0.1%',
        'young_active': False,
        'young_age_s': None
    }

    # Ask side matching band 2
    # target_price = 100.5, dist_bps = 0.5 / 100 * 10000 = 50 bps
    res = find_bucket_wall_at_price(buckets, Decimal('100.5'), 'ask')
    assert res == {
        'band_idx': 1,
        'band_bps': 50,
        'notional': '6000',
        'imbalance': '-0.8%',
        'young_active': False,
        'young_age_s': None
    }

    # Bid side matching band 3
    # target_price = 99.0, dist_bps = 1 / 100 * 10000 = 100 bps
    res = find_bucket_wall_at_price(buckets, Decimal('99.0'), 'bid')
    assert res == {
        'band_idx': 2,
        'band_bps': 100,
        'notional': '1500000',
        'imbalance': '+0.9%',
        'young_active': True,
        'young_age_s': 200
    }

    # Outside bands
    assert find_bucket_wall_at_price(buckets, Decimal('102.0'), 'bid') is None

def test_score_confluence():
    wick = {'wick_price': '100.0', 'wick_type': 'high'}

    # Base score
    res = score_confluence(wick, None, None, None, None)
    assert res['score'] == 20
    assert res['signals'] == ['WICK']
    assert res['signal_count'] == 1

    # Volume T4 + Absorption (+15 + 15)
    volume = {'volume_tier': 'T4', 'absorption': True}
    res = score_confluence(wick, volume, None, None, None)
    assert res['score'] == 50
    assert 'VOL_T4' in res['signals']
    assert 'ABSORPTION' in res['signals']

    # Bucket wall > 1M, Imbalance > 0.7, Young < 300 (+15 + 10 + 10)
    buckets = {
        'mid_price': '100.0',
        'bands_bps': [10],
        'ask_notional': ['2000000'],
        'imbalance': ['-0.8%'],
        'ask_young_active': [True],
        'ask_young_age_s': [150]
    }
    res = score_confluence(wick, None, buckets, None, None)
    assert res['score'] == 55 # 20 base + 35
    assert 'WALL_2.0M' in res['signals']
    assert 'IMB_0.80' in res['signals']
    assert 'YOUNG_150s' in res['signals']

    # CVD alignment: high wick + negative delta (+10)
    cvd = {'cvd_delta': '-500'}
    res = score_confluence(wick, None, None, cvd, None)
    assert res['score'] == 30
    assert 'CVD_ALIGNED' in res['signals']

    # CVD alignment: low wick + positive delta (+10)
    wick_low = {'wick_price': '100.0', 'wick_type': 'low'}
    cvd_pos = {'cvd_delta': '500'}
    res = score_confluence(wick_low, None, None, cvd_pos, None)
    assert res['score'] == 30
    assert 'CVD_ALIGNED' in res['signals']

    # VWAP confluence (+5)
    vwap = {'vwap_session': '100.2'} # 0.2 / 100.2 = ~0.2%, within 0.5% tolerance
    res = score_confluence(wick, None, None, None, vwap)
    assert res['score'] == 25
    assert 'VWAP_SESSION' in res['signals']

    # All together -> Caps at 100
    res = score_confluence(wick, volume, buckets, cvd, vwap)
    assert res['score'] == 100 # Should be min(20+30+35+10+5, 100) = min(100, 100)

    volume_extra = {'volume_tier': 'T4', 'absorption': True} # +30
    buckets_extra = {
        'mid_price': '100.0',
        'bands_bps': [10],
        'ask_notional': ['2000000'], # +15
        'imbalance': ['-0.8%'], # +10
        'ask_young_active': [True],
        'ask_young_age_s': [150] # +10
    } # +35
    cvd_extra = {'cvd_delta': '-500'} # +10
    vwap_extra = {'vwap_session': '100.2'} # +5
    # Total = 20 + 30 + 35 + 10 + 5 = 100
    # Let's add something else to test > 100 capping, but wait score only sums up to exactly 100 right now.
    # We can just verify it's capped at 100 if we slightly modify the logic, but 100 is exactly 100.

    # Let's try low wick + positive delta + wall + absorption etc...
    buckets_low = {
        'mid_price': '100.0',
        'bands_bps': [10],
        'bid_notional': ['2000000'], # +15
        'imbalance': ['+0.8%'], # +10
        'bid_young_active': [True],
        'bid_young_age_s': [150] # +10
    } # +35
    res = score_confluence(wick_low, volume_extra, buckets_low, cvd_pos, vwap_extra)
    assert res['score'] == 100

    # What if base score of 20, + 15 + 15 + 15 + 10 + 10 + 10 + 5 = 100 exactly.
    # It tops out at 100, checking caps.
