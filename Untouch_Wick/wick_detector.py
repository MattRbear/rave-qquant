"""
Wick Detector - Frozen Rules V1 (PATCHED)
------------------------------------------
Detects ALL wicks (any size, no filters).
Tracks multi-variant touch with tip_distance_ticks + penetration_ticks.
State machine: untouched → touched → expired (168h).
"""

import json
import logging
from pathlib import Path
from decimal import Decimal, getcontext
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict

from candle_builder import Candle

# Set high precision
getcontext().prec = 50

# Logging
logger = logging.getLogger('Wick_Detector')


@dataclass
class WickEvent:
    """Wick event with full touch metadata (FROZEN RULES V1)."""
    event_id: str  # {INSTID}|{TF}|{window_end_utc}|{wick_type}
    instId: str
    timeframe: str
    creation_time_utc: str
    window_end_utc: str
    
    wick_type: str  # 'high' or 'low'
    wick_price: str
    wick_size: str
    body_size: str
    
    candle_open: str
    candle_high: str
    candle_low: str
    candle_close: str
    
    status: str  # 'untouched' | 'touched' | 'expired'
    
    # Touch metadata (null when untouched)
    touch_time_utc: Optional[str] = None
    age_at_touch_minutes: Optional[int] = None
    
    touch_by_wick: Optional[bool] = None
    touch_by_body: Optional[bool] = None
    touch_class: Optional[str] = None  # 'wick' | 'body' | 'both'
    
    # Tip metrics (null when tickSz missing or no wick touch)
    tip_distance_ticks: Optional[float] = None
    tip_exact: Optional[bool] = None
    tip_near: Optional[bool] = None
    signal_strength: Optional[str] = None  # 'EXACT' | 'NEAR' | 'CLOSE' | 'TOUCHED'
    penetration_ticks: Optional[int] = None
    
    tickSz: str = '0'
    tol_tip_ticks: int = 1  # ±1 tick tolerance


def detect_wicks(candle: Candle, tickSz: str) -> List[WickEvent]:
    """
    Detect ALL wicks in candle (no size filter).
    Returns list of WickEvent (0, 1, or 2 wicks per candle).
    
    Event ID format: {INSTID}|{TF}|{window_end_utc}|{wick_type}
    """
    wicks = []
    
    # Convert to Decimal
    o = candle.open_decimal
    h = candle.high_decimal
    l = candle.low_decimal
    c = candle.close_decimal
    
    # Body range
    body_max = max(o, c)
    body_min = min(o, c)
    body_size = abs(c - o)
    
    # Upper wick
    upper_wick_size = h - body_max
    if upper_wick_size > 0:
        event_id = f"{candle.instId}|{candle.timeframe}|{candle.window_end_utc}|high"
        
        wick = WickEvent(
            event_id=event_id,
            instId=candle.instId,
            timeframe=candle.timeframe,
            creation_time_utc=candle.window_end_utc,
            window_end_utc=candle.window_end_utc,
            wick_type='high',
            wick_price=str(h),
            wick_size=str(upper_wick_size),
            body_size=str(body_size),
            candle_open=candle.open,
            candle_high=candle.high,
            candle_low=candle.low,
            candle_close=candle.close,
            status='untouched',
            tickSz=tickSz
        )
        wicks.append(wick)
    
    # Lower wick
    lower_wick_size = body_min - l
    if lower_wick_size > 0:
        event_id = f"{candle.instId}|{candle.timeframe}|{candle.window_end_utc}|low"
        
        wick = WickEvent(
            event_id=event_id,
            instId=candle.instId,
            timeframe=candle.timeframe,
            creation_time_utc=candle.window_end_utc,
            window_end_utc=candle.window_end_utc,
            wick_type='low',
            wick_price=str(l),
            wick_size=str(lower_wick_size),
            body_size=str(body_size),
            candle_open=candle.open,
            candle_high=candle.high,
            candle_low=candle.low,
            candle_close=candle.close,
            status='untouched',
            tickSz=tickSz
        )
        wicks.append(wick)
    
    return wicks
