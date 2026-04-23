import time
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from VWAP.vwap_calculator import RollingWindow, SessionWindow, Trade

def generate_trades(num_trades):
    trades = []
    base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    for i in range(num_trades):
        t = base_time + timedelta(seconds=i)
        trade = Trade(
            timestamp_utc=t.isoformat(),
            exchange="okx",
            market="perp",
            instId="BTC-USDT-SWAP",
            symbol_canon="BTC",
            trade_id=str(i),
            side="buy",
            price="50000.0",
            qty_contracts="1",
            ctVal="0.01",
            ctMult="1",
            ctType="linear"
        )
        trades.append(trade)
    return trades

def run_benchmark():
    trades = generate_trades(10000)

    window = RollingWindow(60)

    start_time = time.time()
    for trade in trades:
        window.add_trade(trade)
        window.trim_to_window(trade.timestamp)
        vwap = window.calculate_vwap()
    end_time = time.time()

    print(f"Time taken for 10000 trades: {end_time - start_time:.4f} seconds")

if __name__ == '__main__':
    run_benchmark()
