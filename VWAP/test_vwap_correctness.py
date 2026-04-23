import unittest
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from vwap_calculator import Trade, SessionWindow, RollingWindow, AnchoredWindow
import random

class TestVWAPCorrectness(unittest.TestCase):
    def generate_dummy_trades(self, count: int):
        base_time = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        trades = []
        for i in range(count):
            trade_time = base_time + timedelta(seconds=i)
            trade = Trade(
                timestamp_utc=trade_time.isoformat().replace('+00:00', 'Z'),
                exchange='okx',
                market='perp',
                instId='BTC-USDT-SWAP',
                symbol_canon='BTC-USDT-SWAP',
                trade_id=str(i),
                side='buy' if random.random() > 0.5 else 'sell',
                price=str(20000 + random.random() * 100),
                qty_contracts='1',
                ctVal='0.01',
                ctMult='1',
                ctType='linear'
            )
            trades.append(trade)
        return trades

    def test_session_window(self):
        sw = SessionWindow()
        trades = self.generate_dummy_trades(100)

        # Test first day
        for trade in trades[:50]:
            sw.add_trade(trade)

        expected_vwap = sw.calculate_vwap()
        self.assertIsNotNone(expected_vwap)

        # Test session reset
        reset_trade_time = datetime(2023, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        reset_trade = Trade(
            timestamp_utc=reset_trade_time.isoformat().replace('+00:00', 'Z'),
            exchange='okx', market='perp', instId='BTC-USDT-SWAP', symbol_canon='BTC-USDT-SWAP',
            trade_id='reset', side='buy', price='21000', qty_contracts='1', ctVal='0.01',
            ctMult='1', ctType='linear'
        )
        sw.add_trade(reset_trade)
        self.assertEqual(len(sw.trades), 1)
        self.assertEqual(sw.calculate_vwap(), Decimal('21000'))

    def test_rolling_window(self):
        rw = RollingWindow(1) # 1 minute
        trades = self.generate_dummy_trades(120) # 2 minutes of trades

        for trade in trades:
            rw.add_trade(trade)
            rw.trim_to_window(trade.timestamp)

            # Manual calculation for verification
            sum_pv = Decimal('0')
            sum_v = Decimal('0')
            for t in rw.trades:
                notional = t.notional
                sum_pv += t.price_decimal * notional
                sum_v += notional

            expected = sum_pv / sum_v if sum_v != 0 else None
            result = rw.calculate_vwap()
            if expected is None:
                self.assertIsNone(result)
            else:
                self.assertAlmostEqual(float(result), float(expected), places=10)

    def test_anchored_window(self):
        anchor_time = datetime(2023, 1, 1, 0, 0, 30, tzinfo=timezone.utc)
        aw = AnchoredWindow(anchor_time)
        trades = self.generate_dummy_trades(100)

        for trade in trades:
            aw.add_trade(trade)

        sum_pv = Decimal('0')
        sum_v = Decimal('0')
        valid_trades = [t for t in trades if t.timestamp >= anchor_time]
        for t in valid_trades:
            notional = t.notional
            sum_pv += t.price_decimal * notional
            sum_v += notional

        expected = sum_pv / sum_v if sum_v != 0 else None
        result = aw.calculate_vwap()
        if expected is None:
            self.assertIsNone(result)
        else:
            self.assertAlmostEqual(float(result), float(expected), places=10)

if __name__ == "__main__":
    unittest.main()
