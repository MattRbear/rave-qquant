import pytest
from pathlib import Path
import json
from unittest.mock import patch, mock_open, MagicMock

from VWAP.vwap_calculator import Trade, VWAPState, parse_trades

def test_parse_trades_invalid_trade_data():
    # Prepare dummy data
    state = VWAPState(
        last_timestamp_utc=None,
        last_trade_id=None,
        last_minute_processed=None,
        last_session_date=None
    )

    # 1 valid trade, 1 invalid trade (missing fields), 1 valid trade
    valid_trade_1 = {
        "timestamp_utc": "2023-01-01T00:00:00Z",
        "exchange": "okx",
        "market": "perp",
        "instId": "BTC-USDT-SWAP",
        "symbol_canon": "BTC-USDT-SWAP",
        "trade_id": "1",
        "side": "buy",
        "price": "50000",
        "qty_contracts": "1",
        "ctVal": "0.01",
        "ctMult": "1",
        "ctType": "linear"
    }

    invalid_trade = {
        "timestamp_utc": "2023-01-01T00:00:01Z",
        "exchange": "okx"
        # Missing many required fields
    }

    valid_trade_2 = {
        "timestamp_utc": "2023-01-01T00:00:02Z",
        "exchange": "okx",
        "market": "perp",
        "instId": "BTC-USDT-SWAP",
        "symbol_canon": "BTC-USDT-SWAP",
        "trade_id": "3",
        "side": "sell",
        "price": "50001",
        "qty_contracts": "2",
        "ctVal": "0.01",
        "ctMult": "1",
        "ctType": "linear"
    }

    jsonl_content = f"{json.dumps(valid_trade_1)}\n{json.dumps(invalid_trade)}\n{json.dumps(valid_trade_2)}\n"

    with patch("builtins.open", mock_open(read_data=jsonl_content)):
        with patch("VWAP.vwap_calculator.logger") as mock_logger:
            trades = parse_trades(Path("dummy.jsonl"), state)

            # Should have parsed 2 valid trades
            assert len(trades) == 2
            assert trades[0].trade_id == "1"
            assert trades[1].trade_id == "3"

            # Verify the warning was logged for the invalid trade
            mock_logger.warning.assert_called_once()
            args, _ = mock_logger.warning.call_args
            assert "Skipping invalid trade data at line 2" in args[0]

def test_parse_trades_invalid_json():
    state = VWAPState(
        last_timestamp_utc=None,
        last_trade_id=None,
        last_minute_processed=None,
        last_session_date=None
    )

    valid_trade = {
        "timestamp_utc": "2023-01-01T00:00:00Z",
        "exchange": "okx",
        "market": "perp",
        "instId": "BTC-USDT-SWAP",
        "symbol_canon": "BTC-USDT-SWAP",
        "trade_id": "1",
        "side": "buy",
        "price": "50000",
        "qty_contracts": "1",
        "ctVal": "0.01",
        "ctMult": "1",
        "ctType": "linear"
    }

    jsonl_content = f"{json.dumps(valid_trade)}\n{{invalid json\n"

    with patch("builtins.open", mock_open(read_data=jsonl_content)):
        with patch("VWAP.vwap_calculator.logger") as mock_logger:
            trades = parse_trades(Path("dummy.jsonl"), state)

            assert len(trades) == 1
            assert trades[0].trade_id == "1"

            mock_logger.warning.assert_called_once()
            args, _ = mock_logger.warning.call_args
            assert "Skipping invalid JSON at line 2" in args[0]
