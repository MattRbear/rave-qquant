"""
Volume Analyzer - Adversarial Volume Intelligence
--------------------------------------------------
Reads raw trades, computes volume metrics with intensity classification.

From .txt insights:
- Volume tiers (T1-T4): Classify intensity vs rolling median
- Whale filtering: Isolate trades >$100k for institutional tracking
- Absorption detection: Price flat + volume surge = wall defense
- Divergence detection: Price vs volume direction mismatch = exhaustion

INPUT: Vault\raw\okx\trades_perps\{INSTID}\{DATE}.jsonl
OUTPUT: Vault\derived\volume\okx\perps\{INSTID}\volume_1m.jsonl
STATE: Vault\state\volume\okx\perps\{INSTID}.state.json
"""

import json
import logging
from pathlib import Path
from decimal import Decimal, getcontext
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from collections import deque
import argparse

# Set precision
getcontext().prec = 50

# Paths
VAULT_BASE = Path(r"C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault")

# Thresholds
WHALE_THRESHOLD_USD = Decimal('100000')  # $100k+ = whale
ABSORPTION_PRICE_CHANGE_PCT = Decimal('0.1')  # 0.1% = "flat"
ABSORPTION_VOLUME_MULTIPLIER = Decimal('2.0')  # 2x median = surge

# Volume tier windows
TIER_LOOKBACK_BARS = 100  # Rolling median over 100 bars

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('volume_analyzer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('Volume_Analyzer')


@dataclass
class Trade:
    """Trade from JSONL."""
    timestamp_utc: str
    instId: str
    side: str
    price: str
    qty_contracts: str
    ctVal: str
    
    @property
    def timestamp(self) -> datetime:
        return datetime.fromisoformat(self.timestamp_utc.replace('Z', '+00:00'))
    
    @property
    def notional_usd(self) -> Decimal:
        """Calculate notional in USD."""
        qty = Decimal(self.qty_contracts)
        ct_val = Decimal(self.ctVal)
        price = Decimal(self.price)
        return qty * ct_val * price



@dataclass
class VolumeState:
    """State for incremental processing."""
    last_processed_timestamp_utc: Optional[str]
    last_trade_id: Optional[str]
    last_minute_processed: Optional[str]
    
    # Historical volume for tier calculation
    volume_history: List[str]  # Last 100+ bars


def floor_to_minute(ts: datetime) -> datetime:
    """Floor timestamp to minute."""
    return ts.replace(second=0, microsecond=0)


def load_state(inst_id: str) -> VolumeState:
    """Load state or create new."""
    state_file = VAULT_BASE / 'state' / 'volume' / 'okx' / 'perps' / f'{inst_id}.state.json'
    
    if not state_file.exists():
        return VolumeState(
            last_processed_timestamp_utc=None,
            last_trade_id=None,
            last_minute_processed=None,
            volume_history=[]
        )
    
    with open(state_file, 'r') as f:
        data = json.load(f)
    
    return VolumeState(**data)


def save_state(inst_id: str, state: VolumeState):
    """Save state."""
    state_file = VAULT_BASE / 'state' / 'volume' / 'okx' / 'perps' / f'{inst_id}.state.json'
    state_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(state_file, 'w') as f:
        json.dump({
            'last_processed_timestamp_utc': state.last_processed_timestamp_utc,
            'last_trade_id': state.last_trade_id,
            'last_minute_processed': state.last_minute_processed,
            'volume_history': state.volume_history[-TIER_LOOKBACK_BARS:]  # Trim to window
        }, f, indent=2)



def calculate_mad(values: List[Decimal]) -> Decimal:
    """
    Calculate Median Absolute Deviation (MAD).
    
    RESEARCH FORMULA (Section 6.1):
    1. Calculate median: X̃ = median(X)
    2. Calculate absolute deviations: |Xi - X̃|
    3. Calculate MAD: MAD = median(|Xi - X̃|)
    
    RESEARCH: "MAD is robust to outliers, unlike standard deviation which
    can be blown out by a single massive volatility event (flash crash)."
    """
    if not values:
        return Decimal('0')
    
    # Step 1: Calculate median
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    
    if n % 2 == 0:
        median = (sorted_vals[n//2 - 1] + sorted_vals[n//2]) / Decimal('2')
    else:
        median = sorted_vals[n//2]
    
    # Step 2: Calculate absolute deviations
    abs_deviations = [abs(v - median) for v in values]
    
    # Step 3: Calculate MAD (median of absolute deviations)
    sorted_devs = sorted(abs_deviations)
    n_devs = len(sorted_devs)
    
    if n_devs % 2 == 0:
        mad = (sorted_devs[n_devs//2 - 1] + sorted_devs[n_devs//2]) / Decimal('2')
    else:
        mad = sorted_devs[n_devs//2]
    
    return mad


def calculate_modified_zscore(value: Decimal, values_history: List[Decimal]) -> Optional[Decimal]:
    """
    Calculate Modified Z-Score using MAD (robust to outliers).
    
    RESEARCH FORMULA (Section 6.1):
    Mi = 0.6745 × (Xi - median) / MAD
    
    Where:
    - 0.6745 is scaling constant (makes MAD consistent with σ of normal dist)
    - σ ≈ 1.4826 × MAD
    
    ANOMALY THRESHOLD: |Mi| > 3.5
    
    RESEARCH: "This method reliably detects volume spikes and price anomalies
    without being corrupted by the outliers themselves."
    """
    if not values_history or len(values_history) < 3:
        return None
    
    # Calculate median
    sorted_vals = sorted(values_history)
    n = len(sorted_vals)
    
    if n % 2 == 0:
        median = (sorted_vals[n//2 - 1] + sorted_vals[n//2]) / Decimal('2')
    else:
        median = sorted_vals[n//2]
    
    # Calculate MAD
    mad = calculate_mad(values_history)
    
    if mad == 0:
        return None  # Cannot calculate (all values identical)
    
    # Calculate Modified Z-Score
    # Scaling constant: 0.6745
    modified_z = Decimal('0.6745') * (value - median) / mad
    
    return modified_z


def detect_volume_anomaly(volume: Decimal, volume_history: List[str], 
                          threshold: Decimal = Decimal('3.5')) -> tuple[bool, Optional[Decimal]]:
    """
    Detect volume anomalies using MAD-based Modified Z-Score.
    
    RESEARCH (Section 6.1):
    - Traditional Z-Score fails in heavy-tailed (leptokurtic) distributions
    - Single flash crash can blow out σ, masking subsequent anomalies
    - MAD-based approach is robust to outliers
    
    Returns: (is_anomaly, modified_z_score)
    """
    if not volume_history or len(volume_history) < 3:
        return (False, None)
    
    # Convert history to Decimal
    history_vals = [Decimal(v) for v in volume_history]
    
    # Calculate Modified Z-Score
    modified_z = calculate_modified_zscore(volume, history_vals)
    
    if modified_z is None:
        return (False, None)
    
    # Check threshold
    is_anomaly = abs(modified_z) > threshold
    
    return (is_anomaly, modified_z)


def calculate_volume_tier(volume: Decimal, volume_history: List[str]) -> str:
    """
    Classify volume intensity into tiers (T1-T4).
    
    T1: Normal (< 0.5x median)
    T2: Above average (0.5x - 1.0x median)
    T3: High (1.0x - 2.0x median)
    T4: Extreme (> 2.0x median) - WHALE TERRITORY
    """
    if not volume_history:
        return 'T2'  # Default to mid-tier
    
    # Calculate median from history
    history_vals = [Decimal(v) for v in volume_history]
    history_vals.sort()
    
    n = len(history_vals)
    if n % 2 == 0:
        median = (history_vals[n//2 - 1] + history_vals[n//2]) / Decimal('2')
    else:
        median = history_vals[n//2]
    
    if median == 0:
        return 'T2'
    
    # Classify
    ratio = volume / median
    
    if ratio > Decimal('2.0'):
        return 'T4'  # Extreme
    elif ratio > Decimal('1.0'):
        return 'T3'  # High
    elif ratio > Decimal('0.5'):
        return 'T2'  # Above average
    else:
        return 'T1'  # Normal


def detect_absorption(price_change_pct: Decimal, volume: Decimal, 
                      volume_history: List[str]) -> bool:
    """
    Detect absorption: Price flat but volume surging.
    
    Signal: Whale wall absorbing aggression.
    """
    if not volume_history:
        return False
    
    # Price must be nearly flat
    if abs(price_change_pct) > ABSORPTION_PRICE_CHANGE_PCT:
        return False
    
    # Volume must be elevated
    history_vals = [Decimal(v) for v in volume_history]
    if not history_vals:
        return False
    
    median = sorted(history_vals)[len(history_vals)//2]
    
    if median == 0:
        return False
    
    # Volume > 2x median = surge
    if volume > median * ABSORPTION_VOLUME_MULTIPLIER:
        return True
    
    return False


def detect_divergence(price_change_pct: Decimal, delta: Decimal) -> bool:
    """
    Detect divergence: Price and volume delta moving opposite directions.
    
    Examples:
    - Price up (+) but delta down (-) = Buyers exhausted (SHORT)
    - Price down (-) but delta up (+) = Sellers exhausted (LONG)
    """
    if price_change_pct == 0 or delta == 0:
        return False
    
    # Opposite signs = divergence
    return (price_change_pct > 0 and delta < 0) or (price_change_pct < 0 and delta > 0)



def read_trade_files(inst_id: str) -> List[Path]:
    """Get all trade JSONL files."""
    trade_dir = VAULT_BASE / 'raw' / 'okx' / 'trades_perps' / inst_id
    
    if not trade_dir.exists():
        return []
    
    files = sorted(trade_dir.glob('*.jsonl'))
    return files


def parse_trades(filepath: Path, state: VolumeState) -> List[Trade]:
    """Parse trades from JSONL, filtering to new trades only."""
    trades = []
    
    with open(filepath, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            
            try:
                data = json.loads(line)
                
                # Skip if before cursor
                if state.last_processed_timestamp_utc:
                    if data['timestamp_utc'] < state.last_processed_timestamp_utc:
                        continue
                    
                    if data['timestamp_utc'] == state.last_processed_timestamp_utc:
                        if state.last_trade_id and data.get('trade_id', '') <= state.last_trade_id:
                            continue
                
                trade = Trade(
                    timestamp_utc=data['timestamp_utc'],
                    instId=data['instId'],
                    side=data['side'],
                    price=data['price'],
                    qty_contracts=data['qty_contracts'],
                    ctVal=data['ctVal']
                )
                
                trades.append(trade)
            
            except Exception as e:
                logger.error(f"Error parsing trade: {e}")
                continue
    
    return trades



def aggregate_minute(trades: List[Trade], minute_ts: datetime) -> Dict:
    """
    Aggregate trades for one minute window.
    
    Returns volume metrics including:
    - Total, buy, sell volume
    - Whale volume (>$100k trades)
    - Volume tier
    - Absorption/divergence flags
    """
    if not trades:
        return None
    
    # Initialize accumulators
    total_volume = Decimal('0')
    buy_volume = Decimal('0')
    sell_volume = Decimal('0')
    whale_volume = Decimal('0')
    whale_count = 0
    
    prices = []
    
    for trade in trades:
        notional = trade.notional_usd
        total_volume += notional
        
        # Classify by side
        if trade.side == 'buy':
            buy_volume += notional
        else:
            sell_volume += notional
        
        # Whale filtering
        if notional >= WHALE_THRESHOLD_USD:
            whale_volume += notional
            whale_count += 1
        
        prices.append(Decimal(trade.price))
    
    # Price metrics
    open_price = prices[0]
    close_price = prices[-1]
    high_price = max(prices)
    low_price = min(prices)
    
    # Price change %
    price_change_pct = ((close_price - open_price) / open_price) * Decimal('100')
    
    # Volume delta
    delta = buy_volume - sell_volume
    
    return {
        'timestamp_utc': minute_ts.strftime('%Y-%m-%dT%H:%M:00Z'),
        'open': str(open_price),
        'high': str(high_price),
        'low': str(low_price),
        'close': str(close_price),
        'price_change_pct': str(price_change_pct),
        'total_volume': str(total_volume),
        'buy_volume': str(buy_volume),
        'sell_volume': str(sell_volume),
        'delta': str(delta),
        'whale_volume': str(whale_volume),
        'whale_count': whale_count,
        'trade_count': len(trades)
    }



def write_volume_output(inst_id: str, volume_data: Dict):
    """Write volume metrics to JSONL (append-only)."""
    output_dir = VAULT_BASE / 'derived' / 'volume' / 'okx' / 'perps' / inst_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'volume_1m.jsonl'
    
    # Check if already written
    if output_file.exists():
        with open(output_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                if data.get('timestamp_utc') == volume_data['timestamp_utc']:
                    return  # Already written
    
    # Append
    with open(output_file, 'a') as f:
        f.write(json.dumps(volume_data) + '\n')


def process_inst_id(inst_id: str):
    """
    Main processing loop.
    
    1. Load state
    2. Read trade files
    3. Parse new trades
    4. Aggregate by minute
    5. Calculate tiers + signals
    6. Write output
    7. Update state
    """
    logger.info(f"Processing volume for {inst_id}")
    
    # Load state
    state = load_state(inst_id)
    logger.info(f"State loaded: last_processed={state.last_processed_timestamp_utc}")
    
    # Read trade files
    trade_files = read_trade_files(inst_id)
    
    if not trade_files:
        logger.warning(f"No trade files found for {inst_id}")
        return
    
    logger.info(f"Found {len(trade_files)} trade files")
    
    # Parse all trades
    all_trades = []
    for filepath in trade_files:
        trades = parse_trades(filepath, state)
        all_trades.extend(trades)
    
    if not all_trades:
        logger.info(f"No new trades to process for {inst_id}")
        return
    
    # Sort by timestamp
    all_trades.sort(key=lambda t: (t.timestamp_utc, t.instId))
    
    logger.info(f"Processing {len(all_trades)} new trades")

    
    # Group trades by minute
    trades_by_minute = {}
    
    for trade in all_trades:
        minute = floor_to_minute(trade.timestamp)
        
        if minute not in trades_by_minute:
            trades_by_minute[minute] = []
        
        trades_by_minute[minute].append(trade)
    
    # Process each minute
    outputs_written = 0
    
    for minute_ts in sorted(trades_by_minute.keys()):
        # Skip if already processed
        if state.last_minute_processed:
            last_minute = datetime.fromisoformat(state.last_minute_processed.replace('Z', '+00:00'))
            if minute_ts <= last_minute:
                continue
        
        minute_trades = trades_by_minute[minute_ts]
        
        # Aggregate minute
        agg = aggregate_minute(minute_trades, minute_ts)
        
        if not agg:
            continue
        
        # Calculate volume tier
        tier = calculate_volume_tier(
            Decimal(agg['total_volume']),
            state.volume_history
        )
        
        # Detect volume anomaly using MAD (RESEARCH: Section 6.1)
        is_anomaly, modified_z = detect_volume_anomaly(
            Decimal(agg['total_volume']),
            state.volume_history
        )
        
        # Detect absorption
        absorption = detect_absorption(
            Decimal(agg['price_change_pct']),
            Decimal(agg['total_volume']),
            state.volume_history
        )
        
        # Detect divergence
        divergence = detect_divergence(
            Decimal(agg['price_change_pct']),
            Decimal(agg['delta'])
        )
        
        # Build output
        volume_data = {
            **agg,
            'instId': inst_id,
            'exchange': 'okx',
            'market': 'perp',
            'volume_tier': tier,
            'volume_anomaly': is_anomaly,
            'modified_z_score': str(modified_z) if modified_z is not None else None,
            'absorption': absorption,
            'divergence': divergence
        }
        
        # Write output
        write_volume_output(inst_id, volume_data)
        outputs_written += 1
        
        # Update state
        state.volume_history.append(agg['total_volume'])
        state.last_minute_processed = agg['timestamp_utc']
    
    # Update state with last trade
    if all_trades:
        last_trade = all_trades[-1]
        state.last_processed_timestamp_utc = last_trade.timestamp_utc
        state.last_trade_id = getattr(last_trade, 'trade_id', None)
    
    # Save state
    save_state(inst_id, state)
    
    logger.info(f"Processing complete for {inst_id}")
    logger.info(f"Wrote {outputs_written} volume records\n")



def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Volume Analyzer - Intensity Classification + Absorption Detection')
    parser.add_argument('--instId', required=True, help='Instrument ID (BTC-USDT-SWAP or ETH-USDT-SWAP)')
    
    args = parser.parse_args()
    
    try:
        process_inst_id(args.instId)
    except Exception as e:
        logger.error(f"Error processing {args.instId}: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
