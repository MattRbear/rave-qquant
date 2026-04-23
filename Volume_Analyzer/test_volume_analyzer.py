import pytest
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone
import json
import tempfile
import os

from volume_analyzer import _should_skip_trade, _parse_trade_line, VolumeState, Trade

@pytest.fixture
def sample_trade_data():
    return {
        "timestamp_utc": "2023-01-01T12:00:00Z",
        "instId": "BTC-USDT-SWAP",
        "side": "buy",
        "price": "50000.0",
        "qty_contracts": "1",
        "ctVal": "0.001"
    }

def test_should_skip_trade(sample_trade_data):
    # No state cursor, shouldn't skip
    state1 = VolumeState(last_processed_timestamp_utc=None, last_trade_id=None, last_minute_processed=None, volume_history=[])
    assert not _should_skip_trade(sample_trade_data, state1)

    # Cursor is in the future, should skip
    state2 = VolumeState(last_processed_timestamp_utc="2023-01-01T12:00:01Z", last_trade_id=None, last_minute_processed=None, volume_history=[])
    assert _should_skip_trade(sample_trade_data, state2)

    # Cursor is in the past, shouldn't skip
    state3 = VolumeState(last_processed_timestamp_utc="2023-01-01T11:59:59Z", last_trade_id=None, last_minute_processed=None, volume_history=[])
    assert not _should_skip_trade(sample_trade_data, state3)

    # Cursor is same time, check trade ID
    sample_with_id = sample_trade_data.copy()
    sample_with_id['trade_id'] = "1000"

    state4 = VolumeState(last_processed_timestamp_utc="2023-01-01T12:00:00Z", last_trade_id="1000", last_minute_processed=None, volume_history=[])
    assert _should_skip_trade(sample_with_id, state4) # Same ID, skip

    state5 = VolumeState(last_processed_timestamp_utc="2023-01-01T12:00:00Z", last_trade_id="0999", last_minute_processed=None, volume_history=[])
    assert not _should_skip_trade(sample_with_id, state5) # Newer ID, don't skip

def test_parse_trade_line(sample_trade_data):
    line = json.dumps(sample_trade_data)
    state = VolumeState(last_processed_timestamp_utc=None, last_trade_id=None, last_minute_processed=None, volume_history=[])

    trade = _parse_trade_line(line, state)
    assert trade is not None
    assert trade.timestamp_utc == "2023-01-01T12:00:00Z"
    assert trade.instId == "BTC-USDT-SWAP"
    assert trade.side == "buy"
    assert trade.price == "50000.0"
    assert trade.qty_contracts == "1"
    assert trade.ctVal == "0.001"

    # Invalid JSON should return None
    invalid_line = "{invalid json"
    assert _parse_trade_line(invalid_line, state) is None

    # Empty line should return None
    assert _parse_trade_line("   \n", state) is None

    # Skipped trade should return None
    state_future = VolumeState(last_processed_timestamp_utc="2023-01-01T12:00:01Z", last_trade_id=None, last_minute_processed=None, volume_history=[])
    assert _parse_trade_line(line, state_future) is None
