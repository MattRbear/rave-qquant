import pytest
from trades_exporter import TradesWriter, InstrumentMetadata
from unittest.mock import MagicMock
from datetime import datetime, timezone

def test_seen_trades_limit():
    meta_mock = MagicMock(spec=InstrumentMetadata)
    meta_mock.get_contract_params.return_value = {
        'ctVal': '0.01',
        'ctMult': '1',
        'ctType': 'linear'
    }
    writer = TradesWriter(meta_mock)

    # Mock _get_output_path and open to not write files
    writer._get_output_path = MagicMock()

    import builtins
    original_open = builtins.open
    builtins.open = MagicMock()

    try:
        inst_id = "BTC-USDT-SWAP"

        # Write 10001 trades
        for i in range(10001):
            trade_data = {
                'ts': str(int(datetime.now().timestamp() * 1000)),
                'tradeId': str(i),
                'px': '50000',
                'sz': '1',
                'side': 'buy'
            }
            writer.write_trade(inst_id, trade_data)

        # Check size of seen_trades
        assert len(writer.seen_trades[inst_id]) == 5001

    finally:
        builtins.open = original_open
