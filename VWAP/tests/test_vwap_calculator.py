import json
from pathlib import Path
import pytest
import logging
from VWAP.vwap_calculator import parse_trades, VWAPState, Trade

def test_parse_trades_invalid_json(tmp_path, caplog):
    # Set up state
    state = VWAPState(
        last_timestamp_utc=None,
        last_trade_id=None,
        last_minute_processed=None,
        last_session_date=None
    )

    # Create a dummy file with one valid line, one invalid JSON line, and another valid line
    test_file = tmp_path / "test_trades.jsonl"

    valid_trade_1 = {
        "timestamp_utc": "2023-10-01T12:00:00Z",
        "exchange": "okx",
        "market": "perp",
        "instId": "BTC-USDT-SWAP",
        "symbol_canon": "BTC-USDT-PERP",
        "trade_id": "1",
        "side": "buy",
        "price": "30000",
        "qty_contracts": "1",
        "ctVal": "0.01",
        "ctMult": "1",
        "ctType": "linear"
    }

    valid_trade_2 = {
        "timestamp_utc": "2023-10-01T12:01:00Z",
        "exchange": "okx",
        "market": "perp",
        "instId": "BTC-USDT-SWAP",
        "symbol_canon": "BTC-USDT-PERP",
        "trade_id": "2",
        "side": "sell",
        "price": "30010",
        "qty_contracts": "2",
        "ctVal": "0.01",
        "ctMult": "1",
        "ctType": "linear"
    }

    invalid_json_line = '{"timestamp_utc": "2023-10-01T12:00:30Z", "exchange": "okx", "market": "perp", "instId": "BTC-USDT-SWAP", "symbol_canon": "BTC-USDT-PERP", "trade_id": "X", "side": "buy", "price": 30005, ' # truncated, invalid json

    with open(test_file, 'w') as f:
        f.write(json.dumps(valid_trade_1) + '\n')
        f.write(invalid_json_line + '\n')
        f.write(json.dumps(valid_trade_2) + '\n')

    # Parse trades and capture logs
    with caplog.at_level(logging.WARNING):
        trades = parse_trades(test_file, state)

    # Assertions
    assert len(trades) == 2, "Expected exactly 2 valid trades to be parsed"
    assert trades[0].trade_id == "1"
    assert trades[1].trade_id == "2"

    # Verify the warning log for skipping invalid JSON
    warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
    assert len(warning_logs) >= 1

    # check that the invalid JSON log specifically was recorded
    invalid_json_logs = [log for log in warning_logs if "Skipping invalid JSON" in log.message]
    assert len(invalid_json_logs) == 1
    assert "Skipping invalid JSON at line 2" in invalid_json_logs[0].message
