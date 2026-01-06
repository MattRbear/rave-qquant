r"""
VWAP Calculator - Tick-VWAP with Session + Rolling Windows
-----------------------------------------------------------
Implements research-verified VWAP calculations:
1. Tick-VWAP: Σ(Pi × Vi) / Σ(Vi) - NO Typical Price approximation
2. Session VWAP: Resets at 00:00 UTC daily (institutional standard)
3. Rolling VWAP: 1h and 4h windows
4. Anchored VWAP: Custom t₀ for event-based analysis

RESEARCH COMPLIANCE:
- Uses exact trade prices (not OHLC approximation)
- UTC-anchored sessions for global consistency
- Proper notional weighting: qty_contracts × ctVal × price

INPUT: Vault\raw\okx\trades_perps\{INSTID}\{DATE}.jsonl
OUTPUT: Vault\derived\vwap\okx\perps\{INSTID}\vwap_1m.jsonl
STATE: Vault\state\vwap\okx\perps\{INSTID}.state.json
"""

import json
import logging
from pathlib import Path
from decimal import Decimal, getcontext
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass
from collections import deque
import argparse

# Set high precision for Decimal operations
getcontext().prec = 50

# Configuration
VAULT_BASE = Path(r"C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault")

# Window sizes (minutes)
WINDOW_1H = 60
WINDOW_4H = 240

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('VWAP_Calculator')


@dataclass
class Trade:
    """Trade record from JSONL."""
    timestamp_utc: str  # ISO format
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
    def notional(self) -> Decimal:
        """
        Calculate notional value.
        notional = qty_contracts × ctVal × price
        
        RESEARCH: This is the EXACT formula required for proper volume weighting.
        """
        qty = Decimal(self.qty_contracts)
        ct_val = Decimal(self.ctVal)
        price = Decimal(self.price)
        
        return qty * ct_val * price
    
    @property
    def price_decimal(self) -> Decimal:
        """Price as Decimal."""
        return Decimal(self.price)


@dataclass
class VWAPState:
    """State tracker for VWAP calculation."""
    last_timestamp_utc: Optional[str]  # ISO format
    last_trade_id: Optional[str]
    last_minute_processed: Optional[str]  # ISO minute timestamp
    last_session_date: Optional[str]  # YYYY-MM-DD for session tracking


def floor_to_midnight_utc(ts: datetime) -> datetime:
    """
    Floor timestamp to midnight UTC (00:00:00).
    
    RESEARCH: "Standard institutional VWAP in crypto resets at 00:00 UTC.
    This ensures global data parity and consistent support/resistance levels."
    """
    return ts.replace(hour=0, minute=0, second=0, microsecond=0)


def floor_to_minute(ts: datetime) -> datetime:
    """Floor timestamp to nearest minute."""
    return ts.replace(second=0, microsecond=0)


class SessionWindow:
    """
    Session-anchored VWAP window (resets at 00:00 UTC daily).
    
    RESEARCH: Session VWAP represents the average entry price of all participants
    since the daily session start. Used as psychological support/resistance by
    institutional traders.
    """
    
    def __init__(self):
        self.trades: deque[Trade] = deque()
        self.current_session_date: Optional[str] = None
    
    def check_and_reset_session(self, trade_time: datetime):
        """Reset trades if new UTC day."""
        trade_date = trade_time.date().isoformat()
        
        if self.current_session_date is None:
            self.current_session_date = trade_date
        elif trade_date != self.current_session_date:
            # New session - reset
            logger.info(f"Session reset: {self.current_session_date} → {trade_date}")
            self.trades.clear()
            self.current_session_date = trade_date
    
    def add_trade(self, trade: Trade):
        """Add trade to session window."""
        self.check_and_reset_session(trade.timestamp)
        self.trades.append(trade)
    
    def calculate_vwap(self) -> Optional[Decimal]:
        """
        Calculate session VWAP.
        VWAP = Σ(price × notional) / Σ(notional)
        """
        if not self.trades:
            return None
        
        sum_price_volume = Decimal('0')
        sum_volume = Decimal('0')
        
        for trade in self.trades:
            notional = trade.notional
            price = trade.price_decimal
            
            sum_price_volume += price * notional
            sum_volume += notional
        
        if sum_volume == 0:
            return None
        
        return sum_price_volume / sum_volume
    
    def get_trade_count(self) -> int:
        """Get number of trades in current session."""
        return len(self.trades)


class RollingWindow:
    """
    Rolling window for VWAP calculation (1h or 4h).
    
    RESEARCH: Maintains fixed time window using deque. While not the most
    efficient implementation (subtractive method would be faster), this approach
    is mathematically correct and handles all edge cases properly.
    """
    
    def __init__(self, window_minutes: int):
        self.window_minutes = window_minutes
        self.trades: deque[Trade] = deque()
    
    def add_trade(self, trade: Trade):
        """Add trade to window."""
        self.trades.append(trade)
    
    def trim_to_window(self, current_time: datetime):
        """Remove trades older than window size."""
        cutoff_time = current_time - timedelta(minutes=self.window_minutes)
        
        # Remove from left (oldest) while they're outside window
        while self.trades and self.trades[0].timestamp < cutoff_time:
            self.trades.popleft()
    
    def calculate_vwap(self) -> Optional[Decimal]:
        """
        Calculate VWAP for current window.
        
        RESEARCH FORMULA: VWAP_tick = Σ(Pi × Vi) / Σ(Vi)
        This is the ABSOLUTE definition - uses exact trade prices, not OHLC approximation.
        """
        if not self.trades:
            return None
        
        sum_price_volume = Decimal('0')
        sum_volume = Decimal('0')
        
        for trade in self.trades:
            notional = trade.notional
            price = trade.price_decimal
            
            sum_price_volume += price * notional
            sum_volume += notional
        
        if sum_volume == 0:
            return None
        
        return sum_price_volume / sum_volume
    
    def get_trade_count(self) -> int:
        """Get number of trades in window."""
        return len(self.trades)


class AnchoredWindow:
    """
    Anchored VWAP window (custom start time t₀).
    
    RESEARCH: "Anchored VWAP allows the user to define t₀, the start time of
    the calculation, based on a significant market event (e.g., a CPI release
    or a pump initiation). This metric is psychologically potent as it represents
    the average entry price of all participants since the specific event."
    
    NOTE: Currently stores all trades since anchor. For production use on long
    timeframes (weeks+), consider periodic state snapshots to limit memory.
    """
    
    def __init__(self, anchor_time: Optional[datetime] = None):
        self.anchor_time = anchor_time
        self.trades: List[Trade] = []
    
    def set_anchor(self, anchor_time: datetime):
        """Set anchor time and clear trades."""
        self.anchor_time = anchor_time
        self.trades.clear()
        logger.info(f"AVWAP anchor set: {anchor_time.isoformat()}")
    
    def add_trade(self, trade: Trade):
        """Add trade if after anchor time."""
        if self.anchor_time is None:
            return
        
        if trade.timestamp >= self.anchor_time:
            self.trades.append(trade)
    
    def calculate_vwap(self) -> Optional[Decimal]:
        """
        Calculate anchored VWAP.
        AVWAP_t = Σ(from t₀ to t) (Pi × Vi) / Σ(from t₀ to t) Vi
        """
        if not self.trades or self.anchor_time is None:
            return None
        
        sum_price_volume = Decimal('0')
        sum_volume = Decimal('0')
        
        for trade in self.trades:
            notional = trade.notional
            price = trade.price_decimal
            
            sum_price_volume += price * notional
            sum_volume += notional
        
        if sum_volume == 0:
            return None
        
        return sum_price_volume / sum_volume
    
    def get_trade_count(self) -> int:
        """Get number of trades since anchor."""
        return len(self.trades)


def load_state(inst_id: str) -> VWAPState:
    """Load state for instrument, or create new if doesn't exist."""
    state_file = VAULT_BASE / 'state' / 'vwap' / 'okx' / 'perps' / f'{inst_id}.state.json'
    
    if not state_file.exists():
        return VWAPState(
            last_timestamp_utc=None,
            last_trade_id=None,
            last_minute_processed=None,
            last_session_date=None
        )
    
    with open(state_file, 'r') as f:
        data = json.load(f)
    
    # Handle old state files without session tracking
    if 'last_session_date' not in data:
        data['last_session_date'] = None
    
    return VWAPState(**data)


def save_state(inst_id: str, state: VWAPState):
    """Save state for instrument."""
    state_file = VAULT_BASE / 'state' / 'vwap' / 'okx' / 'perps' / f'{inst_id}.state.json'
    state_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(state_file, 'w') as f:
        json.dump({
            'last_timestamp_utc': state.last_timestamp_utc,
            'last_trade_id': state.last_trade_id,
            'last_minute_processed': state.last_minute_processed,
            'last_session_date': state.last_session_date
        }, f, indent=2)


def read_trade_files(inst_id: str) -> List[Path]:
    """Get all trade JSONL files for instrument, sorted by date."""
    trade_dir = VAULT_BASE / 'raw' / 'okx' / 'trades_perps' / inst_id
    
    if not trade_dir.exists():
        return []
    
    # Get all JSONL files, sorted by name (YYYY-MM-DD.jsonl)
    files = sorted(trade_dir.glob('*.jsonl'))
    return files


def parse_trades(filepath: Path, state: VWAPState) -> List[Trade]:
    """
    Read trades from JSONL file.
    Only return trades AFTER the state cursor.
    """
    trades = []
    
    with open(filepath, 'r') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping invalid JSON at line {line_num}: {e}")
                continue
            
            try:
                trade = Trade(**data)
            except Exception as e:
                logger.warning(f"Skipping invalid trade data at line {line_num}: {e}")
                continue
            
            # Skip if before or equal to cursor
            if state.last_timestamp_utc is not None:
                if trade.timestamp_utc < state.last_timestamp_utc:
                    continue
                
                if trade.timestamp_utc == state.last_timestamp_utc:
                    # Same timestamp - check trade_id
                    if state.last_trade_id is not None:
                        if trade.trade_id <= state.last_trade_id:
                            continue
            
            trades.append(trade)
    
    return trades


def write_vwap_output(inst_id: str, minute_ts: datetime, 
                      vwap_session: Optional[Decimal],
                      vwap_1h: Optional[Decimal], 
                      vwap_4h: Optional[Decimal],
                      trade_count_session: int,
                      trade_count_1h: int,
                      trade_count_4h: int):
    """
    Write VWAP output to derived JSONL.
    Deduplicates by checking if minute already written.
    
    OUTPUT FORMAT:
    - vwap_session: Daily session VWAP (resets 00:00 UTC)
    - vwap_1h: Rolling 60-minute VWAP
    - vwap_4h: Rolling 240-minute VWAP
    """
    output_dir = VAULT_BASE / 'derived' / 'vwap' / 'okx' / 'perps' / inst_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'vwap_1m.jsonl'
    
    minute_str = minute_ts.strftime('%Y-%m-%dT%H:%M:00Z')
    
    # Check if this minute already exists in output
    if output_file.exists():
        with open(output_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                if data.get('window_start_utc') == minute_str:
                    return  # Already written
    
    # Build VWAP record
    vwap_record = {
        'window_start_utc': minute_str,
        'instId': inst_id,
        'exchange': 'okx',
        'market': 'perp',
        'vwap_session': str(vwap_session) if vwap_session is not None else None,
        'vwap_1h': str(vwap_1h) if vwap_1h is not None else None,
        'vwap_4h': str(vwap_4h) if vwap_4h is not None else None,
        'trade_count_session': trade_count_session,
        'trade_count_1h': trade_count_1h,
        'trade_count_4h': trade_count_4h
    }
    
    # Append to output file
    with open(output_file, 'a') as f:
        f.write(json.dumps(vwap_record) + '\n')


def process_inst_id(inst_id: str, anchor_time: Optional[str] = None):
    """
    Main processing loop for an instrument.
    
    PROCESS:
    1. Load state (tracks last processed trade)
    2. Read trade files
    3. Parse new trades only
    4. Maintain ALL windows (session + rolling + optional anchor)
    5. Output VWAP every minute
    6. Update state
    
    RESEARCH COMPLIANCE:
    - Session VWAP resets at 00:00 UTC (institutional standard)
    - Rolling windows use exact trades (no OHLC approximation)
    - All timestamps explicitly UTC for global consistency
    """
    logger.info(f"Processing VWAP for {inst_id}")
    
    # Load state
    state = load_state(inst_id)
    logger.info(f"Loaded state: last_ts={state.last_timestamp_utc}, last_minute={state.last_minute_processed}")
    
    # Initialize windows
    window_session = SessionWindow()
    window_1h = RollingWindow(WINDOW_1H)
    window_4h = RollingWindow(WINDOW_4H)
    
    # Optional: Anchored VWAP
    window_anchored = None
    if anchor_time:
        anchor_dt = datetime.fromisoformat(anchor_time.replace('Z', '+00:00'))
        window_anchored = AnchoredWindow(anchor_dt)
        logger.info(f"Anchored VWAP enabled: t₀ = {anchor_time}")
    
    # Get trade files
    trade_files = read_trade_files(inst_id)
    if not trade_files:
        logger.warning(f"No trade files found for {inst_id}")
        return
    
    logger.info(f"Found {len(trade_files)} trade files")
    
    # Process all files
    all_trades = []
    for filepath in trade_files:
        trades = parse_trades(filepath, state)
        all_trades.extend(trades)
    
    if not all_trades:
        logger.info(f"No new trades to process for {inst_id}")
        return
    
    # Sort trades by (timestamp, trade_id)
    all_trades.sort(key=lambda t: (t.timestamp_utc, t.trade_id))
    
    logger.info(f"Processing {len(all_trades)} new trades")
    
    # Track current minute for output
    current_minute = None
    vwap_outputs = 0
    
    for trade in all_trades:
        trade_minute = floor_to_minute(trade.timestamp)
        
        # Add trade to all windows
        window_session.add_trade(trade)
        window_1h.add_trade(trade)
        window_4h.add_trade(trade)
        
        if window_anchored:
            window_anchored.add_trade(trade)
        
        # Trim rolling windows to their respective sizes
        window_1h.trim_to_window(trade.timestamp)
        window_4h.trim_to_window(trade.timestamp)
        
        # Check if we've moved to a new minute
        if current_minute is None or trade_minute > current_minute:
            # Skip if this minute was already processed
            if state.last_minute_processed is not None:
                last_minute = datetime.fromisoformat(state.last_minute_processed.replace('Z', '+00:00'))
                if trade_minute <= last_minute:
                    current_minute = trade_minute
                    continue
            
            # Calculate VWAPs for this minute
            vwap_session = window_session.calculate_vwap()
            vwap_1h = window_1h.calculate_vwap()
            vwap_4h = window_4h.calculate_vwap()
            
            # Write output
            write_vwap_output(
                inst_id,
                trade_minute,
                vwap_session,
                vwap_1h,
                vwap_4h,
                window_session.get_trade_count(),
                window_1h.get_trade_count(),
                window_4h.get_trade_count()
            )
            
            vwap_outputs += 1
            current_minute = trade_minute
        
        # Update state with this trade
        state.last_timestamp_utc = trade.timestamp_utc
        state.last_trade_id = trade.trade_id
        state.last_session_date = trade.timestamp.date().isoformat()
    
    # Update last minute processed
    if current_minute is not None:
        state.last_minute_processed = current_minute.strftime('%Y-%m-%dT%H:%M:00Z')
    
    # Save state
    save_state(inst_id, state)
    
    logger.info(f"VWAP processing complete for {inst_id}")
    logger.info(f"Output {vwap_outputs} new 1-minute VWAP records")
    logger.info(f"State updated: last_minute={state.last_minute_processed}, session={state.last_session_date}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Calculate VWAP from trades (Session + Rolling)')
    parser.add_argument('--instId', required=True, help='Instrument ID (e.g., BTC-USDT-SWAP)')
    parser.add_argument('--anchor', required=False, help='Anchor time for AVWAP (ISO format with Z)')
    
    args = parser.parse_args()
    
    try:
        process_inst_id(args.instId, anchor_time=args.anchor)
    except Exception as e:
        logger.error(f"Error processing {args.instId}: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
