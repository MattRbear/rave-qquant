import pytest
import os
import tempfile
import json
from decimal import Decimal
from datetime import datetime, timezone

os.environ['RAVEQUANT_VAULT'] = tempfile.mkdtemp()

from VWAP.vwap_calculator import Trade, SessionWindow, RollingWindow, AnchoredWindow

def create_trade(ts: str, price: str, qty: str):
    return Trade(
        timestamp_utc=ts,
        exchange="okx",
        market="perp",
        instId="BTC-USDT-SWAP",
        symbol_canon="BTC/USDT",
        trade_id="123",
        side="buy",
        price=price,
        qty_contracts=qty,
        ctVal="0.01",
        ctMult="1",
        ctType="linear"
    )

def test_trade_notional():
    trade = create_trade("2024-01-01T12:00:00Z", "50000", "2")
    # notional = 2 * 0.01 * 50000 = 1000
    assert trade.notional == Decimal("1000")

def test_session_window():
    sw = SessionWindow()
    t1 = create_trade("2024-01-01T12:00:00Z", "50000", "2")
    t2 = create_trade("2024-01-01T13:00:00Z", "51000", "1")
    sw.add_trade(t1)
    sw.add_trade(t2)

    vwap = sw.calculate_vwap()
    assert round(vwap, 2) == Decimal("50337.75")

    # New session resets
    t3 = create_trade("2024-01-02T01:00:00Z", "60000", "1")
    sw.add_trade(t3)
    assert sw.get_trade_count() == 1
    assert sw.calculate_vwap() == Decimal("60000")

def test_rolling_window():
    rw = RollingWindow(60) # 60 min
    t1 = create_trade("2024-01-01T12:00:00Z", "50000", "1")
    rw.add_trade(t1)

    # Trim with current time 12:30, t1 should stay
    rw.trim_to_window(datetime.fromisoformat("2024-01-01T12:30:00+00:00"))
    assert rw.get_trade_count() == 1

    # Trim with current time 13:01, t1 should be removed
    rw.trim_to_window(datetime.fromisoformat("2024-01-01T13:01:00+00:00"))
    assert rw.get_trade_count() == 0
