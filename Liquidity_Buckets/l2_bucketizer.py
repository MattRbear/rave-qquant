r"""
L2 Liquidity Bucketizer - Young Walls + Imbalance Detection
------------------------------------------------------------
Reads OKX L2 snapshots, computes bucket metrics with anti-noise filters.

ENHANCEMENTS:
- Persistence filter (30s minimum before "young")
- Imbalance ratios (bid vs ask pressure)
- Significant delta thresholds ($100k or 10%)
- Stale reset (1h max "young" age)
- Asset-specific thresholds (BTC: 300k, ETH: 150k)

INPUT: Vault\raw\okx\l2_perps\{INSTID}\{DATE}.jsonl
OUTPUT: Vault\derived\liquidity_buckets\okx\perps\{INSTID}\{DATE}.jsonl
STATE: Vault\state\liquidity_buckets\okx\perps\{INSTID}.state.json
"""

import json
import logging
from pathlib import Path
from decimal import Decimal, getcontext
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import argparse

# Set high precision
getcontext().prec = 50

# Paths
VAULT_BASE = Path(__file__).resolve().parent.parent / "Rave_Quant_Vault"

# Instruments
INSTRUMENTS = ["BTC-USDT-SWAP", "ETH-USDT-SWAP"]

# Bucket bands (bps from mid)
BANDS_BPS = [10, 25, 50, 100, 200, 500]
NUM_BANDS = len(BANDS_BPS)


# Anti-noise thresholds
MIN_NOTIONAL_BY_ASSET = {
    'BTC-USDT-SWAP': Decimal('300000'),  # BTC deeper market
    'ETH-USDT-SWAP': Decimal('150000')   # ETH thinner market
}

MIN_PERSISTENCE_SECONDS = 30  # Wall must persist 30s before "young"
MAX_YOUNG_AGE_SECONDS = 3600  # 1 hour max "young" age (then stale)

MIN_SIGNIFICANT_DELTA_USD = Decimal('100000')  # $100k absolute
MIN_SIGNIFICANT_DELTA_PCT = Decimal('0.10')    # 10% relative

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('l2_bucketizer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('L2_Bucketizer')


@dataclass
class L2Snapshot:
    """L2 snapshot from raw JSONL."""
    timestamp_utc: str
    instId: str
    mid_price: Optional[str]
    bids: List[List[str]]  # [[price, size], ...]
    asks: List[List[str]]
    
    @property
    def timestamp(self) -> datetime:
        return datetime.fromisoformat(self.timestamp_utc.replace('Z', '+00:00'))



@dataclass
class BucketState:
    """State for incremental processing + young wall tracking."""
    last_processed_timestamp_utc: Optional[str]
    
    # Previous snapshot buckets (for delta calculation)
    prev_bid_notional: List[str]  # Length = NUM_BANDS
    prev_ask_notional: List[str]
    
    # Tentative young walls (waiting for 30s persistence)
    tentative_bid_born_ts: List[Optional[str]]  # ISO or None
    tentative_ask_born_ts: List[Optional[str]]
    
    # Confirmed young walls (persisted 30s+)
    confirmed_bid_born_ts: List[Optional[str]]
    confirmed_ask_born_ts: List[Optional[str]]


def load_metadata(inst_id: str) -> Dict:
    """Load instrument metadata."""
    meta_file = VAULT_BASE / 'meta' / 'okx' / 'instruments' / f'{inst_id}.json'
    
    if not meta_file.exists():
        logger.error(f"BUILD_FAIL: Missing metadata file: {meta_file}")
        raise FileNotFoundError(f"Metadata not found for {inst_id}")
    
    with open(meta_file, 'r') as f:
        data = json.load(f)
    
    if 'normalized' in data:
        return data['normalized']
    
    return data.get('raw', data)



def load_state(inst_id: str) -> BucketState:
    """Load state or create new."""
    state_file = VAULT_BASE / 'state' / 'liquidity_buckets' / 'okx' / 'perps' / f'{inst_id}.state.json'
    
    if not state_file.exists():
        return BucketState(
            last_processed_timestamp_utc=None,
            prev_bid_notional=['0'] * NUM_BANDS,
            prev_ask_notional=['0'] * NUM_BANDS,
            tentative_bid_born_ts=[None] * NUM_BANDS,
            tentative_ask_born_ts=[None] * NUM_BANDS,
            confirmed_bid_born_ts=[None] * NUM_BANDS,
            confirmed_ask_born_ts=[None] * NUM_BANDS
        )
    
    with open(state_file, 'r') as f:
        data = json.load(f)
    
    return BucketState(**data)


def save_state(inst_id: str, state: BucketState):
    """Save state."""
    state_file = VAULT_BASE / 'state' / 'liquidity_buckets' / 'okx' / 'perps' / f'{inst_id}.state.json'
    state_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(state_file, 'w') as f:
        json.dump({
            'last_processed_timestamp_utc': state.last_processed_timestamp_utc,
            'prev_bid_notional': state.prev_bid_notional,
            'prev_ask_notional': state.prev_ask_notional,
            'tentative_bid_born_ts': state.tentative_bid_born_ts,
            'tentative_ask_born_ts': state.tentative_ask_born_ts,
            'confirmed_bid_born_ts': state.confirmed_bid_born_ts,
            'confirmed_ask_born_ts': state.confirmed_ask_born_ts
        }, f, indent=2)



def parse_l2_snapshot(line: str) -> Optional[L2Snapshot]:
    """Parse L2 snapshot from JSONL line."""
    try:
        data = json.loads(line)
        
        # Extract bids/asks (handle different field names)
        bids = data.get('bids_top200') or data.get('bids') or []
        asks = data.get('asks_top200') or data.get('asks') or []
        
        return L2Snapshot(
            timestamp_utc=data['timestamp_utc'],
            instId=data['instId'],
            mid_price=data.get('mid_price'),
            bids=bids,
            asks=asks
        )
    
    except Exception as e:
        logger.error(f"Failed to parse L2 snapshot: {e}")
        return None


def read_l2_files(inst_id: str, since_minutes: int) -> List[Path]:
    """Get L2 files covering time window."""
    l2_dir = VAULT_BASE / 'raw' / 'okx' / 'l2_perps' / inst_id
    
    if not l2_dir.exists():
        return []
    
    # Get all JSONL files
    files = sorted(l2_dir.glob('*.jsonl'))
    return files



def calculate_buckets(snapshot: L2Snapshot, ct_val: Decimal, mid_price: Decimal) -> Tuple[List[str], List[str], List[str], List[str]]:
    """
    Calculate bucket metrics for one snapshot.
    
    Returns: (bid_notional, ask_notional, bid_base, ask_base)
    Each is list of strings, length = NUM_BANDS
    """
    # Initialize buckets
    bid_notional = [Decimal('0')] * NUM_BANDS
    ask_notional = [Decimal('0')] * NUM_BANDS
    bid_base = [Decimal('0')] * NUM_BANDS
    ask_base = [Decimal('0')] * NUM_BANDS
    
    # Process bids (prices <= mid)
    for level in snapshot.bids:
        if len(level) < 2:
            continue
        
        try:
            price = Decimal(level[0])
            qty_contracts = Decimal(level[1])
            
            # Only prices <= mid
            if price > mid_price:
                continue
            
            # Calculate distance in bps
            distance_bps = abs((mid_price - price) / mid_price) * Decimal('10000')
            
            # Skip if too far
            if distance_bps > BANDS_BPS[-1]:
                continue
            
            # Determine band
            band_idx = None
            for i, upper_bps in enumerate(BANDS_BPS):
                if distance_bps <= upper_bps:
                    band_idx = i
                    break
            
            if band_idx is None:
                continue
            
            # Calculate quantities
            base_qty = qty_contracts * ct_val
            notional = base_qty * price
            
            # Add to bucket
            bid_notional[band_idx] += notional
            bid_base[band_idx] += base_qty
        
        except Exception as e:
            logger.error(f"Error processing bid level: {e}")
            continue

    
    # Process asks (prices >= mid)
    for level in snapshot.asks:
        if len(level) < 2:
            continue
        
        try:
            price = Decimal(level[0])
            qty_contracts = Decimal(level[1])
            
            # Only prices >= mid
            if price < mid_price:
                continue
            
            # Calculate distance in bps
            distance_bps = abs((price - mid_price) / mid_price) * Decimal('10000')
            
            # Skip if too far
            if distance_bps > BANDS_BPS[-1]:
                continue
            
            # Determine band
            band_idx = None
            for i, upper_bps in enumerate(BANDS_BPS):
                if distance_bps <= upper_bps:
                    band_idx = i
                    break
            
            if band_idx is None:
                continue
            
            # Calculate quantities
            base_qty = qty_contracts * ct_val
            notional = base_qty * price
            
            # Add to bucket
            ask_notional[band_idx] += notional
            ask_base[band_idx] += base_qty
        
        except Exception as e:
            logger.error(f"Error processing ask level: {e}")
            continue
    
    # Convert to strings
    return (
        [str(n) for n in bid_notional],
        [str(n) for n in ask_notional],
        [str(b) for b in bid_base],
        [str(b) for b in ask_base]
    )



def calculate_obi(best_bid_vol: Decimal, best_ask_vol: Decimal) -> str:
    """
    Calculate Top-of-Book Order Book Imbalance (OBI).
    
    RESEARCH FORMULA (Section 5.1):
    OBI = (V_bid - V_ask) / (V_bid + V_ask)
    
    Range: [-1, +1]
    +1 = All bid volume (extreme buying pressure)
    -1 = All ask volume (extreme selling pressure)
     0 = Balanced
    
    RESEARCH: "OBI approaching +1 indicates strong buying pressure (bid support).
    OBI approaching -1 indicates strong selling pressure (ask resistance)."
    """
    total = best_bid_vol + best_ask_vol
    
    if total == 0:
        return "0.00"
    
    obi = (best_bid_vol - best_ask_vol) / total
    
    # Format with sign
    if obi >= 0:
        return f"+{obi:.4f}"
    else:
        return f"{obi:.4f}"


def calculate_micro_price(best_bid_price: Decimal, best_ask_price: Decimal,
                          best_bid_vol: Decimal, best_ask_vol: Decimal) -> str:
    """
    Calculate Stoikov Micro-Price (Volume-Weighted Fair Value).
    
    RESEARCH FORMULA (Section 5.2):
    P_micro = (V_bid × P_ask + V_ask × P_bid) / (V_bid + V_ask)
    
    CRITICAL LOGIC (note the cross-weighting):
    - High bid volume (V_bid) pulls price TOWARD the ask (P_ask)
    - High ask volume (V_ask) pulls price TOWARD the bid (P_bid)
    
    RATIONALE: If there is massive buying demand (high V_bid), the price
    is likely to tick UP to the ask. Therefore, the "fair" future price
    is closer to the ask.
    
    RESEARCH: "Stoikov's Micro-price adjusts the mid-price based on the
    imbalance and spread to estimate the 'true' fair value."
    """
    total_vol = best_bid_vol + best_ask_vol
    
    if total_vol == 0:
        # Fallback to simple mid-price
        return str((best_bid_price + best_ask_price) / Decimal('2'))
    
    # Cross-weighted formula
    micro_price = (best_bid_vol * best_ask_price + best_ask_vol * best_bid_price) / total_vol
    
    return str(micro_price)


def calculate_imbalance(bid_notional: List[str], ask_notional: List[str]) -> List[str]:
    """
    Calculate imbalance ratio per band.
    imbalance = (bid - ask) / (bid + ask)
    Range: [-1, +1]
    +1 = all bids (buy pressure)
    -1 = all asks (sell pressure)
     0 = balanced
    """
    imbalances = []
    
    for bid_str, ask_str in zip(bid_notional, ask_notional):
        bid = Decimal(bid_str)
        ask = Decimal(ask_str)
        
        total = bid + ask
        if total == 0:
            imbalances.append("0.0")
        else:
            imb = (bid - ask) / total
            # Format with sign
            if imb >= 0:
                imbalances.append(f"+{imb:.2f}")
            else:
                imbalances.append(f"{imb:.2f}")
    
    return imbalances


def calculate_deltas(current: List[str], previous: List[str]) -> Tuple[List[str], List[bool]]:
    """
    Calculate delta vs previous snapshot + significance.
    
    Returns: (deltas, significant_flags)
    """
    deltas = []
    significant = []
    
    for curr_str, prev_str in zip(current, previous):
        curr = Decimal(curr_str)
        prev = Decimal(prev_str)
        
        delta = curr - prev
        deltas.append(f"+{delta}" if delta >= 0 else str(delta))
        
        # Check significance
        is_sig = (
            abs(delta) > MIN_SIGNIFICANT_DELTA_USD or
            (prev > 0 and abs(delta / prev) > MIN_SIGNIFICANT_DELTA_PCT)
        )
        significant.append(is_sig)
    
    return deltas, significant



def update_young_walls(current_notional: List[str], state: BucketState, 
                      current_ts: datetime, inst_id: str, side: str) -> Tuple[List[Optional[int]], List[bool]]:
    """
    Update young wall tracking with persistence filter + stale reset.
    
    Returns: (young_age_s, young_active)
    """
    threshold = MIN_NOTIONAL_BY_ASSET[inst_id]
    
    # Get state arrays for this side
    if side == 'bid':
        tentative_born = state.tentative_bid_born_ts
        confirmed_born = state.confirmed_bid_born_ts
    else:  # ask
        tentative_born = state.tentative_ask_born_ts
        confirmed_born = state.confirmed_ask_born_ts
    
    young_age_s = []
    young_active = []
    
    for i, notional_str in enumerate(current_notional):
        notional = Decimal(notional_str)
        
        # Check if above threshold
        if notional >= threshold:
            # Start tentative timer if not already started
            if tentative_born[i] is None:
                tentative_born[i] = current_ts.strftime('%Y-%m-%dT%H:%M:%SZ')
                young_age_s.append(None)
                young_active.append(False)
            else:
                # Check persistence
                tentative_ts = datetime.fromisoformat(tentative_born[i].replace('Z', '+00:00'))
                duration_s = (current_ts - tentative_ts).total_seconds()
                
                if duration_s >= MIN_PERSISTENCE_SECONDS:
                    # Confirmed! Move to confirmed_born if not already
                    if confirmed_born[i] is None:
                        confirmed_born[i] = tentative_born[i]
                    
                    # Calculate age from confirmed birth
                    confirmed_ts = datetime.fromisoformat(confirmed_born[i].replace('Z', '+00:00'))
                    age_s = (current_ts - confirmed_ts).total_seconds()
                    
                    # Check stale reset
                    if age_s > MAX_YOUNG_AGE_SECONDS:
                        # Stale - reset
                        tentative_born[i] = None
                        confirmed_born[i] = None
                        young_age_s.append(None)
                        young_active.append(False)
                    else:
                        # Active young wall
                        young_age_s.append(int(age_s))
                        young_active.append(True)
                else:
                    # Still tentative (waiting for persistence)
                    young_age_s.append(None)
                    young_active.append(False)
        else:
            # Below threshold - reset
            tentative_born[i] = None
            confirmed_born[i] = None
            young_age_s.append(None)
            young_active.append(False)
    
    return young_age_s, young_active



def write_bucket_output(inst_id: str, snapshot: L2Snapshot, buckets_data: Dict):
    """Write bucket metrics to derived JSONL (append-only)."""
    # Determine output file (daily rotation)
    ts = snapshot.timestamp
    date_str = ts.strftime('%Y-%m-%d')
    
    output_dir = VAULT_BASE / 'derived' / 'liquidity_buckets' / 'okx' / 'perps' / inst_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f'{date_str}.jsonl'
    
    # Append to file
    with open(output_file, 'a') as f:
        f.write(json.dumps(buckets_data) + '\n')


def process_inst_id(inst_id: str, since_minutes: int):
    """
    Main processing loop (incremental + deterministic).
    
    1. Load state + metadata
    2. Read L2 snapshots
    3. Filter to new snapshots (> last_processed)
    4. For each snapshot:
       - Calculate buckets
       - Calculate imbalance
       - Calculate deltas
       - Update young walls (with persistence + stale reset)
       - Write output
    5. Update state
    """
    logger.info(f"Processing liquidity buckets for {inst_id}")
    
    # Load metadata
    metadata = load_metadata(inst_id)
    ct_val_str = metadata.get('ctVal')
    
    if not ct_val_str:
        logger.error(f"BUILD_FAIL: Missing ctVal for {inst_id}")
        return
    
    ct_val = Decimal(ct_val_str)
    logger.info(f"Loaded metadata: ctVal={ct_val}")
    
    # Load state
    state = load_state(inst_id)
    logger.info(f"Loaded state: last_processed={state.last_processed_timestamp_utc}")
    
    # Read L2 files
    l2_files = read_l2_files(inst_id, since_minutes)
    
    if not l2_files:
        logger.warning(f"No L2 files found for {inst_id}")
        return
    
    logger.info(f"Found {len(l2_files)} L2 files")

    
    # Parse all snapshots
    snapshots = []
    seen_timestamps = set()
    
    for filepath in l2_files:
        with open(filepath, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                
                snapshot = parse_l2_snapshot(line)
                if not snapshot:
                    continue
                
                # Skip if before last processed
                if state.last_processed_timestamp_utc:
                    if snapshot.timestamp_utc <= state.last_processed_timestamp_utc:
                        continue
                
                # Dedup by timestamp
                if snapshot.timestamp_utc in seen_timestamps:
                    continue
                
                seen_timestamps.add(snapshot.timestamp_utc)
                snapshots.append(snapshot)
    
    if not snapshots:
        logger.info(f"No new snapshots to process for {inst_id}")
        return
    
    # Sort by timestamp
    snapshots.sort(key=lambda s: s.timestamp_utc)
    
    logger.info(f"Processing {len(snapshots)} new snapshots")
    
    # Process each snapshot
    outputs_written = 0
    
    for snapshot in snapshots:
        # Validate mid_price
        if not snapshot.mid_price:
            logger.warning(f"Skipping snapshot with null mid_price: {snapshot.timestamp_utc}")
            continue
        
        mid_price = Decimal(snapshot.mid_price)
        
        # Calculate buckets
        bid_notional, ask_notional, bid_base, ask_base = calculate_buckets(
            snapshot, ct_val, mid_price
        )
        
        # Calculate top-of-book metrics (RESEARCH: Section 5.1-5.2)
        # Extract best bid/ask from snapshot
        best_bid_price = Decimal('0')
        best_bid_vol = Decimal('0')
        best_ask_price = Decimal('0')
        best_ask_vol = Decimal('0')
        
        if snapshot.bids and len(snapshot.bids[0]) >= 2:
            best_bid_price = Decimal(snapshot.bids[0][0])
            best_bid_vol = Decimal(snapshot.bids[0][1]) * ct_val
        
        if snapshot.asks and len(snapshot.asks[0]) >= 2:
            best_ask_price = Decimal(snapshot.asks[0][0])
            best_ask_vol = Decimal(snapshot.asks[0][1]) * ct_val
        
        # Calculate OBI (Order Book Imbalance)
        obi = calculate_obi(best_bid_vol, best_ask_vol)
        
        # Calculate Micro-Price (Stoikov weighted mid)
        micro_price = calculate_micro_price(best_bid_price, best_ask_price, 
                                            best_bid_vol, best_ask_vol)

        
        # Calculate imbalance
        imbalance = calculate_imbalance(bid_notional, ask_notional)
        
        # Calculate deltas
        bid_delta, bid_delta_sig = calculate_deltas(bid_notional, state.prev_bid_notional)
        ask_delta, ask_delta_sig = calculate_deltas(ask_notional, state.prev_ask_notional)
        
        # Update young walls (with persistence + stale reset)
        bid_young_age, bid_young_active = update_young_walls(
            bid_notional, state, snapshot.timestamp, inst_id, 'bid'
        )
        ask_young_age, ask_young_active = update_young_walls(
            ask_notional, state, snapshot.timestamp, inst_id, 'ask'
        )
        
        # Build output
        buckets_data = {
            'timestamp_utc': snapshot.timestamp_utc,
            'exchange': 'okx',
            'market': 'perp',
            'instId': inst_id,
            'mid_price': snapshot.mid_price,
            'micro_price': micro_price,  # NEW: Stoikov weighted mid
            'obi': obi,  # NEW: Top-of-book imbalance
            'best_bid_price': str(best_bid_price),
            'best_ask_price': str(best_ask_price),
            'best_bid_vol': str(best_bid_vol),
            'best_ask_vol': str(best_ask_vol),
            'bands_bps': BANDS_BPS,
            'bid_notional': bid_notional,
            'ask_notional': ask_notional,
            'bid_base': bid_base,
            'ask_base': ask_base,
            'imbalance': imbalance,
            'bid_delta_notional': bid_delta,
            'ask_delta_notional': ask_delta,
            'bid_delta_significant': bid_delta_sig,
            'ask_delta_significant': ask_delta_sig,
            'bid_young_age_s': bid_young_age,
            'ask_young_age_s': ask_young_age,
            'bid_young_active': bid_young_active,
            'ask_young_active': ask_young_active
        }
        
        # Write output
        write_bucket_output(inst_id, snapshot, buckets_data)
        outputs_written += 1
        
        # Update state for next iteration
        state.prev_bid_notional = bid_notional
        state.prev_ask_notional = ask_notional
        state.last_processed_timestamp_utc = snapshot.timestamp_utc
    
    # Save state
    save_state(inst_id, state)
    
    logger.info(f"Processing complete for {inst_id}")
    logger.info(f"Wrote {outputs_written} bucket records\n")



def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='L2 Liquidity Bucketizer')
    parser.add_argument('--instId', required=True, help='Instrument ID (BTC-USDT-SWAP or ETH-USDT-SWAP)')
    parser.add_argument('--since', default='240m', help='Lookback window (e.g., 240m, 24h)')
    
    args = parser.parse_args()
    
    # Validate instrument
    if args.instId not in INSTRUMENTS:
        logger.error(f"Invalid instId: {args.instId} (allowed: {INSTRUMENTS})")
        return
    
    # Parse since parameter
    since_str = args.since
    if since_str.endswith('m'):
        since_minutes = int(since_str[:-1])
    elif since_str.endswith('h'):
        since_minutes = int(since_str[:-1]) * 60
    else:
        logger.error(f"Invalid --since format: {since_str} (use 240m or 24h)")
        return
    
    try:
        process_inst_id(args.instId, since_minutes)
    except Exception as e:
        logger.error(f"Error processing {args.instId}: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
