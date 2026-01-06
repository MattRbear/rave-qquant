"""
Candle Builder - UTC-Aligned OHLCV from Trades
-----------------------------------------------
Builds 1m candles from raw trades (event-time).
Rolls up deterministically into 5m/15m/1h/4h.

CRITICAL: Decimal math only (no floats).
CRITICAL: Event-time only (timestamp_utc from trades).
CRITICAL: Deterministic (same inputs = same outputs).
"""

import json
import logging
from pathlib import Path
from decimal import Decimal, getcontext
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict

# Set high precision
getcontext().prec = 50

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Candle_Builder')


@dataclass
class Trade:
    """Trade record from JSONL."""
    timestamp_utc: str
    exchange: str
    market: str
    instId: str
    symbol_canon: str
    trade_id: str
    side: str
    price: str
    qty_contracts: str
    ctVal: str
    ctMult: str
    ctType: str
    
    @property
    def timestamp(self) -> datetime:
        """Parse timestamp to datetime."""
        return datetime.fromisoformat(self.timestamp_utc.replace('Z', '+00:00'))
    
    @property
    def price_decimal(self) -> Decimal:
        """Price as Decimal."""
        return Decimal(self.price)


@dataclass
class Candle:
    """OHLCV candle."""
    window_start_utc: str  # ISO format
    window_end_utc: str    # ISO format
    instId: str
    exchange: str
    market: str
    timeframe: str
    
    open: str   # First trade price
    high: str   # Max trade price
    low: str    # Min trade price
    close: str  # Last trade price
    volume: str # Sum qty_contracts
    
    trade_count: int
    
    @property
    def open_decimal(self) -> Decimal:
        return Decimal(self.open)
    
    @property
    def high_decimal(self) -> Decimal:
        return Decimal(self.high)
    
    @property
    def low_decimal(self) -> Decimal:
        return Decimal(self.low)
    
    @property
    def close_decimal(self) -> Decimal:
        return Decimal(self.close)



def floor_to_minute(ts: datetime) -> datetime:
    """Floor timestamp to minute (UTC)."""
    return ts.replace(second=0, microsecond=0)


def floor_to_timeframe(ts: datetime, timeframe: str) -> datetime:
    """Floor timestamp to timeframe boundary (UTC)."""
    minute = ts.replace(second=0, microsecond=0)
    
    if timeframe == '1m':
        return minute
    elif timeframe == '5m':
        # Floor to 5-minute boundary (:00, :05, :10, etc.)
        m = (minute.minute // 5) * 5
        return minute.replace(minute=m)
    elif timeframe == '15m':
        # Floor to 15-minute boundary (:00, :15, :30, :45)
        m = (minute.minute // 15) * 15
        return minute.replace(minute=m)
    elif timeframe == '1h':
        # Floor to hour
        return minute.replace(minute=0)
    elif timeframe == '4h':
        # Floor to 4-hour boundary (00:00, 04:00, 08:00, etc.)
        h = (minute.hour // 4) * 4
        return minute.replace(hour=h, minute=0)
    else:
        raise ValueError(f"Unknown timeframe: {timeframe}")


def build_1m_candles(trades: List[Trade]) -> List[Candle]:
    """
    Build UTC-aligned 1m candles from trades.
    Event-time only (timestamp_utc from trades).
    """
    if not trades:
        return []
    
    # Sort trades by timestamp
    trades_sorted = sorted(trades, key=lambda t: t.timestamp_utc)
    
    # Group trades by minute
    minute_buckets: Dict[datetime, List[Trade]] = defaultdict(list)
    
    for trade in trades_sorted:
        minute = floor_to_minute(trade.timestamp)
        minute_buckets[minute].append(trade)
    
    # Build candles
    candles = []
    
    for window_start, minute_trades in sorted(minute_buckets.items()):
        window_end = window_start + timedelta(minutes=1)
        
        # OHLC from trades
        prices = [t.price_decimal for t in minute_trades]
        open_price = minute_trades[0].price_decimal  # First trade
        high_price = max(prices)
        low_price = min(prices)
        close_price = minute_trades[-1].price_decimal  # Last trade
        
        # Volume (sum qty_contracts)
        volume = sum(Decimal(t.qty_contracts) for t in minute_trades)
        
        candle = Candle(
            window_start_utc=window_start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            window_end_utc=window_end.strftime('%Y-%m-%dT%H:%M:%SZ'),
            instId=minute_trades[0].instId,
            exchange=minute_trades[0].exchange,
            market=minute_trades[0].market,
            timeframe='1m',
            open=str(open_price),
            high=str(high_price),
            low=str(low_price),
            close=str(close_price),
            volume=str(volume),
            trade_count=len(minute_trades)
        )
        
        candles.append(candle)
    
    return candles



def rollup_candles(candles_1m: List[Candle], timeframe: str) -> List[Candle]:
    """
    Roll up 1m candles into higher timeframe.
    Deterministic: O=first, H=max, L=min, C=last, V=sum.
    """
    if not candles_1m:
        return []
    
    if timeframe == '1m':
        return candles_1m  # No rollup needed
    
    # Group 1m candles by HTF window
    htf_buckets: Dict[datetime, List[Candle]] = defaultdict(list)
    
    for candle in candles_1m:
        window_start = datetime.fromisoformat(candle.window_start_utc.replace('Z', '+00:00'))
        htf_start = floor_to_timeframe(window_start, timeframe)
        htf_buckets[htf_start].append(candle)
    
    # Build HTF candles
    htf_candles = []
    
    for htf_start, bucket_candles in sorted(htf_buckets.items()):
        # Sort candles by window_start
        bucket_sorted = sorted(bucket_candles, key=lambda c: c.window_start_utc)
        
        # Determine HTF window end
        if timeframe == '5m':
            htf_end = htf_start + timedelta(minutes=5)
        elif timeframe == '15m':
            htf_end = htf_start + timedelta(minutes=15)
        elif timeframe == '1h':
            htf_end = htf_start + timedelta(hours=1)
        elif timeframe == '4h':
            htf_end = htf_start + timedelta(hours=4)
        else:
            raise ValueError(f"Unknown timeframe: {timeframe}")
        
        # OHLC aggregation
        open_price = bucket_sorted[0].open_decimal  # First candle's open
        high_price = max(c.high_decimal for c in bucket_sorted)
        low_price = min(c.low_decimal for c in bucket_sorted)
        close_price = bucket_sorted[-1].close_decimal  # Last candle's close
        
        # Volume sum
        volume = sum(Decimal(c.volume) for c in bucket_sorted)
        
        # Trade count sum
        trade_count = sum(c.trade_count for c in bucket_sorted)
        
        htf_candle = Candle(
            window_start_utc=htf_start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            window_end_utc=htf_end.strftime('%Y-%m-%dT%H:%M:%SZ'),
            instId=bucket_sorted[0].instId,
            exchange=bucket_sorted[0].exchange,
            market=bucket_sorted[0].market,
            timeframe=timeframe,
            open=str(open_price),
            high=str(high_price),
            low=str(low_price),
            close=str(close_price),
            volume=str(volume),
            trade_count=trade_count
        )
        
        htf_candles.append(htf_candle)
    
    return htf_candles


def build_all_timeframes(trades: List[Trade]) -> Dict[str, List[Candle]]:
    """
    Build candles for all timeframes from trades.
    Returns dict: {'1m': [...], '5m': [...], ...}
    """
    # Build 1m base
    candles_1m = build_1m_candles(trades)
    
    if not candles_1m:
        return {tf: [] for tf in ['1m', '5m', '15m', '1h', '4h']}
    
    # Rollup to HTF
    candles_5m = rollup_candles(candles_1m, '5m')
    candles_15m = rollup_candles(candles_1m, '15m')
    candles_1h = rollup_candles(candles_1m, '1h')
    candles_4h = rollup_candles(candles_1m, '4h')
    
    return {
        '1m': candles_1m,
        '5m': candles_5m,
        '15m': candles_15m,
        '1h': candles_1h,
        '4h': candles_4h
    }
