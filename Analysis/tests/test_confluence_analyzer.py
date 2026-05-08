import pytest
from decimal import Decimal
from Analysis.confluence_analyzer import (
    prices_align,
    find_bucket_wall_at_price,
    score_confluence
)

def test_prices_align():
    # Test identical prices
    assert prices_align(Decimal('100'), Decimal('100'), Decimal('0.5'))

    # Test within tolerance
    assert prices_align(Decimal('100'), Decimal('100.4'), Decimal('0.5'))
    assert prices_align(Decimal('100.4'), Decimal('100'), Decimal('0.5'))

    # Test exact tolerance boundary
    assert prices_align(Decimal('100.5'), Decimal('100'), Decimal('0.5'))

    # Test exceeding tolerance
    assert not prices_align(Decimal('100.6'), Decimal('100'), Decimal('0.5'))

    # Test zero price edge case
    assert not prices_align(Decimal('100'), Decimal('0'), Decimal('0.5'))


def test_find_bucket_wall_at_price():
    # Test empty buckets
    assert find_bucket_wall_at_price({}, Decimal('100'), 'bid') is None

    # Test missing or zero mid_price
    assert find_bucket_wall_at_price({'mid_price': '0'}, Decimal('100'), 'bid') is None
    assert find_bucket_wall_at_price({'other': 'data'}, Decimal('100'), 'bid') is None

    # Normal scenario
    buckets = {
        'mid_price': '1000',
        'bands_bps': [10, 50, 100],  # 0.1%, 0.5%, 1%
        # Bid side
        'bid_notional': ['100000', '200000', '300000'],
        'imbalance': ['+0.5', '-0.2', '+0.8'],
        'bid_young_active': [True, False, True],
        'bid_young_age_s': [100, None, 200],
        # Ask side
        'ask_notional': ['50000', '150000', '250000'],
        'ask_young_active': [False, True, False],
        'ask_young_age_s': [None, 300, None]
    }

    # Target price distance: abs(1005 - 1000) / 1000 = 0.5% = 50 bps
    # Should match band index 1 (50)
    result_bid = find_bucket_wall_at_price(buckets, Decimal('1005'), 'bid')
    assert result_bid is not None
    assert result_bid['band_idx'] == 1
    assert result_bid['notional'] == '200000'
    assert result_bid['imbalance'] == '-0.2'
    assert result_bid['young_active'] == False
    assert result_bid['young_age_s'] is None

    # Target price distance: abs(999 - 1000) / 1000 = 0.1% = 10 bps
    # Should match band index 0 (10)
    result_ask = find_bucket_wall_at_price(buckets, Decimal('999'), 'ask')
    assert result_ask is not None
    assert result_ask['band_idx'] == 0
    assert result_ask['notional'] == '50000'
    assert result_ask['imbalance'] == '+0.5'
    assert result_ask['young_active'] == False
    assert result_ask['young_age_s'] is None

    # Distance exceeds all bands (110 bps)
    result_far = find_bucket_wall_at_price(buckets, Decimal('1011'), 'bid')
    assert result_far is None


def test_score_confluence():
    wick_base = {'wick_price': '1000', 'wick_type': 'high'}
    wick_low = {'wick_price': '1000', 'wick_type': 'low'}

    # 1. Base Wick Only
    res = score_confluence(wick_base, None, None, None, None)
    assert res['score'] == 20
    assert 'WICK' in res['signals']

    # 2. Wick + Volume (T4 + Absorption)
    volume_data = {'volume_tier': 'T4', 'absorption': True}
    res = score_confluence(wick_base, volume_data, None, None, None)
    assert res['score'] == 50  # 20 + 15 + 15
    assert 'VOL_T4' in res['signals']
    assert 'ABSORPTION' in res['signals']

    # 3. Wick + Buckets (Wall >1M + Imbalance >0.7 + Young Wall <5min)
    # Target price 1000, mid 1000 -> 0 bps, matches band 0
    buckets_data = {
        'mid_price': '1000',
        'bands_bps': [10],
        'ask_notional': ['1500000'],  # > 1M
        'imbalance': ['+0.8'],        # > 0.7
        'ask_young_active': [True],
        'ask_young_age_s': [200]      # < 300s
    }
    # For 'high' wick, it checks 'ask' side
    res = score_confluence(wick_base, None, buckets_data, None, None)
    assert res['score'] == 55  # 20 + 15 (wall) + 10 (imb) + 10 (young)
    assert 'WALL_1.5M' in res['signals']
    assert 'IMB_0.80' in res['signals']
    assert 'YOUNG_200s' in res['signals']

    # 4. Wick + CVD Aligned (High wick needs negative delta)
    cvd_data = {'cvd_delta': '-500'}
    res = score_confluence(wick_base, None, None, cvd_data, None)
    assert res['score'] == 30  # 20 + 10
    assert 'CVD_ALIGNED' in res['signals']

    # CVD Aligned (Low wick needs positive delta)
    cvd_data_pos = {'cvd_delta': '500'}
    res = score_confluence(wick_low, None, None, cvd_data_pos, None)
    assert res['score'] == 30  # 20 + 10
    assert 'CVD_ALIGNED' in res['signals']

    # CVD Unaligned cases
    res = score_confluence(wick_base, None, None, {'cvd_delta': '500'}, None)
    assert res['score'] == 20
    res = score_confluence(wick_low, None, None, {'cvd_delta': '-500'}, None)
    assert res['score'] == 20

    # 5. Wick + VWAP Confluence
    vwap_data = {'vwap_session': '1004'}  # Within 0.5% tolerance
    res = score_confluence(wick_base, None, None, None, vwap_data)
    assert res['score'] == 25  # 20 + 5
    assert 'VWAP_SESSION' in res['signals']

    # 6. Max Score Cap (All signals together)
    # Base(20) + T4(15) + Abs(15) + Wall(15) + Imb(10) + Young(10) + CVD(10) + VWAP(5) = 100
    res = score_confluence(wick_base, volume_data, buckets_data, cvd_data, vwap_data)
    assert res['score'] == 100
    assert len(res['signals']) == 8

    # Test capping over 100
    # Let's say we had even more points (theoretically impossible with current config but min(100) logic exists)
    # We will simulate by using same inputs, max score is already 100.
    assert res['score'] <= 100
