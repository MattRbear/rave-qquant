import json
from decimal import Decimal
from datetime import datetime, timezone
import pytest

from Liquidity_Buckets.l2_bucketizer import (
    parse_l2_snapshot,
    calculate_obi,
    calculate_micro_price,
    calculate_imbalance,
    calculate_deltas,
    calculate_buckets,
    update_young_walls,
    L2Snapshot,
    BucketState,
    MIN_SIGNIFICANT_DELTA_USD,
    MIN_SIGNIFICANT_DELTA_PCT,
    MIN_PERSISTENCE_SECONDS,
    MAX_YOUNG_AGE_SECONDS,
    NUM_BANDS
)

def test_parse_l2_snapshot_valid():
    line = json.dumps({
        "timestamp_utc": "2024-04-20T12:00:00Z",
        "instId": "BTC-USDT-SWAP",
        "mid_price": "60000",
        "bids": [["59900", "1.5"]],
        "asks": [["60100", "2.0"]]
    })

    snapshot = parse_l2_snapshot(line)
    assert snapshot is not None
    assert snapshot.timestamp_utc == "2024-04-20T12:00:00Z"
    assert snapshot.instId == "BTC-USDT-SWAP"
    assert snapshot.mid_price == "60000"
    assert snapshot.bids == [["59900", "1.5"]]
    assert snapshot.asks == [["60100", "2.0"]]
    assert snapshot.timestamp == datetime(2024, 4, 20, 12, 0, 0, tzinfo=timezone.utc)


def test_parse_l2_snapshot_alternative_fields():
    line = json.dumps({
        "timestamp_utc": "2024-04-20T12:00:00Z",
        "instId": "ETH-USDT-SWAP",
        "mid_price": "3000",
        "bids_top200": [["2990", "10.0"]],
        "asks_top200": [["3010", "15.0"]]
    })

    snapshot = parse_l2_snapshot(line)
    assert snapshot is not None
    assert snapshot.bids == [["2990", "10.0"]]
    assert snapshot.asks == [["3010", "15.0"]]


def test_parse_l2_snapshot_invalid():
    # Invalid JSON
    assert parse_l2_snapshot("invalid json") is None

    # Missing required fields
    line = json.dumps({"bids": [], "asks": []})
    assert parse_l2_snapshot(line) is None


def test_calculate_obi():
    # 0 volume -> "0.00"
    assert calculate_obi(Decimal('0'), Decimal('0')) == "0.00"

    # All bid -> "+1.0000"
    assert calculate_obi(Decimal('100'), Decimal('0')) == "+1.0000"

    # All ask -> "-1.0000"
    assert calculate_obi(Decimal('0'), Decimal('100')) == "-1.0000"

    # Balanced -> "+0.0000"
    assert calculate_obi(Decimal('50'), Decimal('50')) == "+0.0000"

    # Imbalanced
    assert calculate_obi(Decimal('75'), Decimal('25')) == "+0.5000"
    assert calculate_obi(Decimal('25'), Decimal('75')) == "-0.5000"


def test_calculate_micro_price():
    # Fallback to simple mid if 0 volume
    assert calculate_micro_price(
        Decimal('100'), Decimal('102'), Decimal('0'), Decimal('0')
    ) == "101"

    # High bid volume pulls to ask
    assert calculate_micro_price(
        Decimal('100'), Decimal('102'), Decimal('90'), Decimal('10')
    ) == "101.8"

    # High ask volume pulls to bid
    assert calculate_micro_price(
        Decimal('100'), Decimal('102'), Decimal('10'), Decimal('90')
    ) == "100.2"


def test_calculate_imbalance():
    bids = ["100", "0", "50", "0", "75", "25"]
    asks = ["0", "100", "50", "0", "25", "75"]

    imbalances = calculate_imbalance(bids, asks)

    assert imbalances[0] == "+1.00" # All bids
    assert imbalances[1] == "-1.00" # All asks
    assert imbalances[2] == "+0.00" # Balanced
    assert imbalances[3] == "0.0"   # Both 0
    assert imbalances[4] == "+0.50"
    assert imbalances[5] == "-0.50"


def test_calculate_deltas():
    # Setup values
    curr = ["150000", "10", "10", "100", "1000"]
    prev = ["10", "150000", "10", "90", "100"] # Delta 1: > 100k abs, Delta 2: < -100k abs, Delta 3: 0, Delta 4: > 10% rel, Delta 5: > 10% rel

    deltas, sigs = calculate_deltas(curr, prev)

    assert deltas[0] == "+149990"
    assert sigs[0] == True # > MIN_SIGNIFICANT_DELTA_USD

    assert deltas[1] == "-149990"
    assert sigs[1] == True # > MIN_SIGNIFICANT_DELTA_USD

    assert deltas[2] == "+0"
    assert sigs[2] == False

    assert deltas[3] == "+10"
    assert sigs[3] == True # (100-90)/90 > 10%

    assert deltas[4] == "+900"
    assert sigs[4] == True # > 10%

def test_calculate_buckets():
    snapshot = L2Snapshot(
        timestamp_utc="2024-01-01T00:00:00Z",
        instId="BTC-USDT-SWAP",
        mid_price="60000",
        bids=[
            ["59970", "1"], # dist = 30/60000 = 5 bps -> band 0
            ["59800", "2"], # dist = 200/60000 = 33.3 bps -> band 2
            ["50000", "10"] # dist = > 500 bps -> skipped
        ],
        asks=[
            ["60060", "3"], # dist = 60/60000 = 10 bps -> band 0
            ["60300", "4"], # dist = 300/60000 = 50 bps -> band 2
            ["70000", "10"] # dist = > 500 bps -> skipped
        ]
    )

    ct_val = Decimal("0.01") # e.g. 1 contract = 0.01 BTC
    mid = Decimal("60000")

    bid_notional, ask_notional, bid_base, ask_base = calculate_buckets(snapshot, ct_val, mid)

    # Bid checks
    # Band 0 (<= 10 bps): 1 contract * 0.01 = 0.01 BTC. Notional = 0.01 * 59970 = 599.7
    assert bid_base[0] == "0.01"
    assert bid_notional[0] == "599.70"

    # Band 2 (<= 50 bps): 2 contracts * 0.01 = 0.02 BTC. Notional = 0.02 * 59800 = 1196.0
    assert bid_base[2] == "0.02"
    assert bid_notional[2] == "1196.00"

    # Band 1 should be 0
    assert bid_base[1] == "0"
    assert bid_notional[1] == "0"

    # Ask checks
    # Band 0 (<= 10 bps): 3 contracts * 0.01 = 0.03 BTC. Notional = 0.03 * 60060 = 1801.8
    assert ask_base[0] == "0.03"
    assert ask_notional[0] == "1801.80"

    # Band 2 (<= 50 bps): 4 contracts * 0.01 = 0.04 BTC. Notional = 0.04 * 60300 = 2412.0
    assert ask_base[2] == "0.04"
    assert ask_notional[2] == "2412.00"


def test_update_young_walls():
    inst_id = "BTC-USDT-SWAP" # MIN_NOTIONAL_BY_ASSET = 300,000

    state = BucketState(
        last_processed_timestamp_utc=None,
        prev_bid_notional=['0'] * NUM_BANDS,
        prev_ask_notional=['0'] * NUM_BANDS,
        tentative_bid_born_ts=[None] * NUM_BANDS,
        tentative_ask_born_ts=[None] * NUM_BANDS,
        confirmed_bid_born_ts=[None] * NUM_BANDS,
        confirmed_ask_born_ts=[None] * NUM_BANDS
    )

    # Test 1: New wall below threshold -> no active wall
    ts1 = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    notionals = ["100000"] + ["0"] * (NUM_BANDS - 1)
    ages, active = update_young_walls(notionals, state, ts1, inst_id, "bid")

    assert active[0] == False
    assert state.tentative_bid_born_ts[0] is None

    # Test 2: Wall goes above threshold -> tentative started
    ts2 = datetime(2024, 1, 1, 0, 0, 10, tzinfo=timezone.utc)
    notionals = ["350000"] + ["0"] * (NUM_BANDS - 1)
    ages, active = update_young_walls(notionals, state, ts2, inst_id, "bid")

    assert active[0] == False
    assert state.tentative_bid_born_ts[0] == "2024-01-01T00:00:10Z"
    assert state.confirmed_bid_born_ts[0] is None

    # Test 3: Wall persists < 30s -> still tentative
    ts3 = datetime(2024, 1, 1, 0, 0, 30, tzinfo=timezone.utc) # 20s diff
    ages, active = update_young_walls(notionals, state, ts3, inst_id, "bid")

    assert active[0] == False
    assert state.confirmed_bid_born_ts[0] is None

    # Test 4: Wall persists >= 30s -> confirmed and active
    ts4 = datetime(2024, 1, 1, 0, 0, 45, tzinfo=timezone.utc) # 35s diff
    ages, active = update_young_walls(notionals, state, ts4, inst_id, "bid")

    assert active[0] == True
    assert ages[0] == 35 # 35s old
    assert state.confirmed_bid_born_ts[0] == "2024-01-01T00:00:10Z"

    # Test 5: Wall persists > 1h -> stale reset
    ts5 = datetime(2024, 1, 1, 1, 1, 0, tzinfo=timezone.utc) # 1h+ diff
    ages, active = update_young_walls(notionals, state, ts5, inst_id, "bid")

    assert active[0] == False
    assert state.tentative_bid_born_ts[0] is None
    assert state.confirmed_bid_born_ts[0] is None

    # Test 6: Wall drops below threshold -> reset
    # First get it back above threshold and confirmed
    update_young_walls(notionals, state, ts1, inst_id, "bid") # start
    update_young_walls(notionals, state, datetime(2024, 1, 1, 0, 1, 0, tzinfo=timezone.utc), inst_id, "bid") # confirm
    assert state.confirmed_bid_born_ts[0] is not None

    # Now drop below threshold
    notionals = ["100000"] + ["0"] * (NUM_BANDS - 1)
    ages, active = update_young_walls(notionals, state, datetime(2024, 1, 1, 0, 2, 0, tzinfo=timezone.utc), inst_id, "bid")

    assert active[0] == False
    assert state.tentative_bid_born_ts[0] is None
    assert state.confirmed_bid_born_ts[0] is None
