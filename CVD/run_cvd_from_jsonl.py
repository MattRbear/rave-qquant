"""
CVD Calculator from JSONL - Research-Verified Implementation
------------------------------------------------------------
Calculates Cumulative Volume Delta (CVD) using aggressor-tagged trades.

RESEARCH COMPLIANCE:
Section 3: CVD is a sentiment indicator derived from order flow mechanics.
- Uses "Taker" side to determine aggression (pays spread to initiate)
- Buy-side aggression ADDS to CVD (aggressive buyers)
- Sell-side aggression SUBTRACTS from CVD (aggressive sellers)
- CVD is CUMULATIVE and NEVER resets (maintains state across sessions)

FORMULA:
  Δt = V_ask,t - V_bid,t
  CVD_T = Σ(t=0 to T) Δt
  
  Where:
  - V_ask,t = volume from market BUY orders (aggressor)
  - V_bid,t = volume from market SELL orders (aggressor)

INPUT: Vault\\raw\\okx\\trades\\{SYMBOL}\\{DATE}.jsonl
OUTPUT: Vault\\derived\\cvd\\okx\\{SYMBOL}\\1m\\{DATE}.jsonl
STATE: Vault\\state\\cvd\\okx\\{SYMBOL}.state.json
"""

import json
import logging
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
from dataclasses import dataclass
import argparse

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('CVD_Calculator')

# Paths
VAULT_BASE = Path(r"C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault")


@dataclass
class CVDState:
    """State tracker for CVD calculation."""
    last_timestamp_utc: Optional[str]  # ISO format
    last_trade_id: Optional[str]
    last_cvd: str  # Decimal as string for JSON


@dataclass
class Trade:
    """
    Trade record from JSONL.
    
    RESEARCH: The 'side' field identifies the AGGRESSOR (Taker).
    - 'buy' = market buy order hit limit sell (aggressive buyer)
    - 'sell' = market sell order hit limit buy (aggressive seller)
    """
    exchange: str
    symbol: str
    trade_id: str
    timestamp_utc: str  # ISO format
    price: str
    size: str
    side: str  # 'buy' or 'sell' (AGGRESSOR side)
    
    @property
    def timestamp(self) -> datetime:
        """Parse timestamp to datetime."""
        return datetime.fromisoformat(self.timestamp_utc.replace('Z', '+00:00'))


def floor_to_minute(ts: datetime) -> datetime:
    """Floor timestamp to nearest minute."""
    return ts.replace(second=0, microsecond=0)


def load_state(symbol: str) -> CVDState:
    """Load state for symbol, or create new if doesn't exist."""
    state_file = VAULT_BASE / 'state' / 'cvd' / 'okx' / f'{symbol}.state.json'
    
    if not state_file.exists():
        return CVDState(
            last_timestamp_utc=None,
            last_trade_id=None,
            last_cvd="0"
        )
    
    with open(state_file, 'r') as f:
        data = json.load(f)
    
    return CVDState(**data)


def save_state(symbol: str, state: CVDState):
    """Save state for symbol."""
    state_file = VAULT_BASE / 'state' / 'cvd' / 'okx' / f'{symbol}.state.json'
    state_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(state_file, 'w') as f:
        json.dump({
            'last_timestamp_utc': state.last_timestamp_utc,
            'last_trade_id': state.last_trade_id,
            'last_cvd': state.last_cvd
        }, f, indent=2)


def read_trade_files(symbol: str) -> List[Path]:
    """Get all trade JSONL files for symbol, sorted by date."""
    trade_dir = VAULT_BASE / 'raw' / 'okx' / 'trades' / symbol
    
    if not trade_dir.exists():
        return []
    
    # Get all JSONL files, sorted by name (YYYY-MM-DD.jsonl)
    files = sorted(trade_dir.glob('*.jsonl'))
    return files


def parse_trades(filepath: Path, state: CVDState) -> List[Trade]:
    """
    Read trades from JSONL file.
    Only return trades AFTER the state cursor (strictly increasing by timestamp, trade_id).
    """
    trades = []
    
    with open(filepath, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            
            data = json.loads(line)
            trade = Trade(**data)
            
            # Skip if before or equal to cursor
            if state.last_timestamp_utc is not None:
                if trade.timestamp_utc < state.last_timestamp_utc:
                    continue
                
                if trade.timestamp_utc == state.last_timestamp_utc:
                    # Same timestamp - check trade_id (numeric comparison)
                    if state.last_trade_id is not None:
                        if int(trade.trade_id) <= int(state.last_trade_id):
                            continue
            
            trades.append(trade)
    
    return trades


def calculate_cvd_updates(trades: List[Trade], start_cvd: Decimal) -> Dict[datetime, tuple[Decimal, Decimal]]:
    """
    Calculate CVD and Delta for each 1m window.
    
    RESEARCH FORMULA:
    - Δt = V_ask,t - V_bid,t
    - CVD_T = CVD_{T-1} + Δt
    
    Returns dict of {window_start: (cvd_value, delta_value)}
    """
    cvd = start_cvd
    windows = {}
    
    # Track per-minute aggregates
    current_minute = None
    minute_buy_volume = Decimal('0')
    minute_sell_volume = Decimal('0')
    
    for trade in trades:
        trade_minute = floor_to_minute(trade.timestamp)
        
        # New minute - save previous
        if current_minute is not None and trade_minute > current_minute:
            delta = minute_buy_volume - minute_sell_volume
            windows[current_minute] = (cvd, delta)
            
            # Reset minute aggregates
            minute_buy_volume = Decimal('0')
            minute_sell_volume = Decimal('0')
        
        trade_size_usd = Decimal(trade.price) * Decimal(trade.size)

        # Update CVD (cumulative)
        if trade.side == 'buy':
            cvd += trade_size_usd
            minute_buy_volume += trade_size_usd
        elif trade.side == 'sell':
            cvd -= trade_size_usd
            minute_sell_volume += trade_size_usd
        else:
            logger.warning(f"Unknown side: {trade.side} for trade {trade.trade_id}")
            continue
        
        current_minute = trade_minute
    
    # Save last minute
    if current_minute is not None:
        delta = minute_buy_volume - minute_sell_volume
        windows[current_minute] = (cvd, delta)
    
    return windows


def write_cvd_outputs(symbol: str, windows: Dict[datetime, tuple[Decimal, Decimal]]):
    """
    Write CVD outputs to derived/cvd/okx/{symbol}/1m/YYYY-MM-DD.jsonl
    Deduplicates by reading existing file first and only appending new windows.
    
    OUTPUT FORMAT:
    - cvd_value: Cumulative volume delta (never resets)
    - cvd_delta: Delta for this 1m bar (buy_vol - sell_vol)
    """
    if not windows:
        return 0
    
    # Group by date
    by_date: Dict[str, Dict[datetime, tuple[Decimal, Decimal]]] = {}
    for window_start, (cvd_value, delta_value) in windows.items():
        date_str = window_start.strftime('%Y-%m-%d')
        if date_str not in by_date:
            by_date[date_str] = {}
        by_date[date_str][window_start] = (cvd_value, delta_value)
    
    total_written = 0
    
    for date_str, date_windows in by_date.items():
        output_dir = VAULT_BASE / 'derived' / 'cvd' / 'okx' / symbol / '1m'
        output_file = output_dir / f'{date_str}.jsonl'
        
        # Read existing windows to deduplicate
        existing_windows = set()
        if output_file.exists():
            with open(output_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    existing_windows.add(data['window_start_utc'])
        
        # Write new windows only
        with open(output_file, 'a') as f:
            for window_start, (cvd_value, delta_value) in sorted(date_windows.items()):
                window_str = window_start.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                if window_str in existing_windows:
                    continue  # Skip duplicate
                
                record = {
                    'window_start_utc': window_str,
                    'cvd_value': str(cvd_value),
                    'cvd_delta': str(delta_value),
                    'symbol': symbol.replace('-', '/'),
                    'exchange': 'okx',
                    'timeframe': '1m'
                }
                
                f.write(json.dumps(record) + '\n')
                total_written += 1
    
    return total_written


def process_symbol(symbol: str):
    """
    Main processing loop for a symbol.
    
    PROCESS:
    1. Load state (tracks last processed trade and CVD value)
    2. Read trade files
    3. Parse new trades only (incremental)
    4. Calculate CVD (cumulative) and Delta (per bar)
    5. Write outputs (deduplicated)
    6. Update state
    
    RESEARCH: CVD is cumulative across sessions. State ensures continuity.
    """
    logger.info(f"Processing CVD for {symbol}")
    
    # Load state
    state = load_state(symbol)
    logger.info(f"Loaded state: last_ts={state.last_timestamp_utc}, last_id={state.last_trade_id}, cvd={state.last_cvd}")
    
    # Get trade files
    trade_files = read_trade_files(symbol)
    if not trade_files:
        logger.warning(f"No trade files found for {symbol}")
        return
    
    logger.info(f"Found {len(trade_files)} trade files")
    
    # Process all files
    all_trades = []
    for filepath in trade_files:
        trades = parse_trades(filepath, state)
        all_trades.extend(trades)
    
    if not all_trades:
        logger.info(f"No new trades to process for {symbol}")
        return
    
    # Sort trades strictly by (timestamp, trade_id numeric)
    all_trades.sort(key=lambda t: (t.timestamp_utc, int(t.trade_id)))
    
    logger.info(f"Processing {len(all_trades)} new trades")
    
    # Calculate CVD updates
    start_cvd = Decimal(state.last_cvd)
    windows = calculate_cvd_updates(all_trades, start_cvd)
    
    # Write outputs (deduplicated)
    written = write_cvd_outputs(symbol, windows)
    logger.info(f"Wrote {written} new 1m CVD windows")
    
    # Update state with last trade
    last_trade = all_trades[-1]
    final_cvd = list(windows.values())[-1][0] if windows else start_cvd  # Extract CVD from tuple
    
    new_state = CVDState(
        last_timestamp_utc=last_trade.timestamp_utc,
        last_trade_id=last_trade.trade_id,
        last_cvd=str(final_cvd)
    )
    
    save_state(symbol, new_state)
    logger.info(f"State updated: cvd={new_state.last_cvd}")
    logger.info(f"CVD processing complete for {symbol}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Calculate CVD from JSONL trade files')
    parser.add_argument('--symbol', required=True, help='Symbol (e.g., BTC-USDT)')
    
    args = parser.parse_args()
    
    try:
        process_symbol(args.symbol)
    except Exception as e:
        logger.error(f"Error processing {args.symbol}: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
