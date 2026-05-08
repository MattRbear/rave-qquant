from decimal import Decimal
from Analysis.confluence_analyzer import (
    prices_align,
    find_bucket_wall_at_price,
    score_confluence
)


# Tests for prices_align
def test_prices_align_exact_match():
    assert prices_align(Decimal('100.0'), Decimal('100.0'), Decimal('0.5'))


def test_prices_align_within_tolerance():
    assert prices_align(Decimal('100.4'), Decimal('100.0'), Decimal('0.5'))
    assert prices_align(Decimal('99.6'), Decimal('100.0'), Decimal('0.5'))


def test_prices_align_outside_tolerance():
    assert not prices_align(Decimal('100.6'), Decimal('100.0'), Decimal('0.5'))
    assert not prices_align(Decimal('99.4'), Decimal('100.0'), Decimal('0.5'))


def test_prices_align_price2_zero():
    assert not prices_align(Decimal('100.0'), Decimal('0'), Decimal('0.5'))


# Tests for find_bucket_wall_at_price
def test_find_bucket_wall_empty_dict():
    assert find_bucket_wall_at_price({}, Decimal('100'), 'bid') is None


def test_find_bucket_wall_zero_mid_price():
    val = find_bucket_wall_at_price({'mid_price': '0'}, Decimal('100'), 'bid')
    assert val is None


def test_find_bucket_wall_bid_side_match():
    buckets = {
        'mid_price': '100',
        'bands_bps': [10, 50, 100],
        'bid_notional': ['1000', '2000', '3000'],
        'imbalance': ['0.5', '0.6', '0.7'],
        'bid_young_active': [False, True, False],
        'bid_young_age_s': [None, 100, None]
    }
    # distance 10 bps -> band 1 (0-10bps)
    # price 99.9 -> diff 0.1 / 100 * 10000 = 10 bps
    res = find_bucket_wall_at_price(buckets, Decimal('99.9'), 'bid')
    assert res is not None
    assert res['band_idx'] == 0
    assert res['notional'] == '1000'

    # distance 30 bps -> band 2 (10-50bps)
    # price 99.7 -> diff 0.3 / 100 * 10000 = 30 bps
    res2 = find_bucket_wall_at_price(buckets, Decimal('99.7'), 'bid')
    assert res2 is not None
    assert res2['band_idx'] == 1
    assert res2['notional'] == '2000'
    assert res2['young_active'] is True
    assert res2['young_age_s'] == 100


def test_find_bucket_wall_ask_side_match():
    buckets = {
        'mid_price': '100',
        'bands_bps': [10, 50, 100],
        'ask_notional': ['1500', '2500', '3500'],
        'imbalance': ['0.5', '0.6', '0.7'],
        'ask_young_active': [False, False, True],
        'ask_young_age_s': [None, None, 50]
    }
    # distance 80 bps -> band 3 (50-100bps)
    # price 100.8 -> diff 0.8 / 100 * 10000 = 80 bps
    res = find_bucket_wall_at_price(buckets, Decimal('100.8'), 'ask')
    assert res is not None
    assert res['band_idx'] == 2
    assert res['notional'] == '3500'
    assert res['young_active'] is True
    assert res['young_age_s'] == 50


# Tests for score_confluence
def test_score_confluence_base_only():
    wick = {'wick_price': '100', 'wick_type': 'high'}
    res = score_confluence(wick, None, None, None, None)
    assert res['score'] == 20
    assert 'WICK' in res['signals']


def test_score_confluence_volume_signals():
    wick = {'wick_price': '100', 'wick_type': 'high'}
    volume = {'volume_tier': 'T4', 'absorption': True}
    res = score_confluence(wick, volume, None, None, None)
    assert res['score'] == 20 + 15 + 15
    assert 'VOL_T4' in res['signals']
    assert 'ABSORPTION' in res['signals']


def test_score_confluence_bucket_signals():
    wick = {'wick_price': '100.2', 'wick_type': 'high'}  # side ask
    # wall > 1M (+15), imbalance > 0.7 (+10), young wall (+10)
    buckets = {
        'mid_price': '100',
        'bands_bps': [30],
        'ask_notional': ['2000000'],
        'imbalance': ['+0.8%'],
        'ask_young_active': [True],
        'ask_young_age_s': [150]
    }
    res = score_confluence(wick, None, buckets, None, None)
    assert res['score'] == 20 + 15 + 10 + 10
    assert 'WALL_2.0M' in res['signals']
    assert 'IMB_0.80' in res['signals']
    assert 'YOUNG_150s' in res['signals']


def test_score_confluence_cvd_alignment():
    wick_high = {'wick_price': '100', 'wick_type': 'high'}
    wick_low = {'wick_price': '100', 'wick_type': 'low'}

    # high wick + negative cvd -> aligned
    cvd_neg = {'cvd_delta': '-1000'}
    res1 = score_confluence(wick_high, None, None, cvd_neg, None)
    assert res1['score'] == 20 + 10
    assert 'CVD_ALIGNED' in res1['signals']

    # high wick + positive cvd -> not aligned
    cvd_pos = {'cvd_delta': '1000'}
    res2 = score_confluence(wick_high, None, None, cvd_pos, None)
    assert res2['score'] == 20
    assert 'CVD_ALIGNED' not in res2['signals']

    # low wick + positive cvd -> aligned
    res3 = score_confluence(wick_low, None, None, cvd_pos, None)
    assert res3['score'] == 20 + 10
    assert 'CVD_ALIGNED' in res3['signals']


def test_score_confluence_vwap_alignment():
    wick = {'wick_price': '100', 'wick_type': 'high'}
    # default tolerance is 0.5% (PRICE_TOLERANCE_PCT = Decimal('0.5'))
    vwap = {'vwap_session': '100.2'}
    res = score_confluence(wick, None, None, None, vwap)
    assert res['score'] == 20 + 5
    assert 'VWAP_SESSION' in res['signals']


def test_score_confluence_max_score_cap():
    wick = {'wick_price': '100', 'wick_type': 'high'}
    volume = {'volume_tier': 'T4', 'absorption': True}  # +30
    buckets = {
        'mid_price': '100',
        'bands_bps': [10],
        'ask_notional': ['2000000'],
        'imbalance': ['+0.8%'],
        'ask_young_active': [True],
        'ask_young_age_s': [150]
    }  # +35
    cvd = {'cvd_delta': '-100'}  # +10
    vwap = {'vwap_session': '100'}  # +5

    res = score_confluence(wick, volume, buckets, cvd, vwap)
    # Total would be 20 + 30 + 35 + 10 + 5 = 100
    assert res['score'] == 100
