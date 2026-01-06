"""
Untouched Wick Bot - PATCHED (Deterministic + Incremental)
----------------------------------------------------------
Fixed Issues:
1. Deterministic: Uses as_of_utc from candles, not datetime.now()
2. Incremental: State cursor per timeframe, only processes NEW candles
3. Null-safe: tip metrics null when tickSz missing (no division by zero)

SCOPE: BTC-USDT-SWAP, ETH-USDT-SWAP (PERPS ONLY)
"""

import json
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Set, Optional
from decimal import Decimal

from candle_builder import Trade, Candle, build_all_timeframes
from wick_detector import WickEvent, detect_wicks

# Paths
VAULT_BASE = Path(r"C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault")

# Configuration
INSTRUMENTS = ["BTC-USDT-SWAP", "ETH-USDT-SWAP"]
TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h']
EXPIRY_HOURS = 168  # 7 days

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('untouch_wick.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('Untouch_Wick')


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
    
    logger.warning(f"No normalized metadata for {inst_id}, using raw")
    return data.get('raw', data)


def load_trades(inst_id: str) -> List[Trade]:
    """Load ALL trades from vault (full history)."""
    trades_dir = VAULT_BASE / 'raw' / 'okx' / 'trades_perps' / inst_id
    
    if not trades_dir.exists():
        logger.warning(f"No trades directory for {inst_id}")
        return []
    
    # Get all JSONL files
    trade_files = sorted(trades_dir.glob('*.jsonl'))
    
    all_trades = []
    
    for filepath in trade_files:
        with open(filepath, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                
                try:
                    data = json.loads(line)
                    trade = Trade(**data)
                    all_trades.append(trade)
                
                except Exception as e:
                    logger.error(f"Failed to parse trade: {e}")
    
    logger.info(f"Loaded {len(all_trades)} trades for {inst_id}")
    return all_trades


def load_timeframe_state(inst_id: str, timeframe: str) -> Dict:
    """Load state cursor for specific timeframe."""
    state_file = VAULT_BASE / 'state' / 'wicks' / 'okx' / 'perps' / f'{inst_id}.{timeframe}.state.json'
    
    if not state_file.exists():
        return {'last_processed_window_end_utc': None}
    
    with open(state_file, 'r') as f:
        return json.load(f)


def save_timeframe_state(inst_id: str, timeframe: str, state: Dict):
    """Save state cursor for specific timeframe."""
    state_file = VAULT_BASE / 'state' / 'wicks' / 'okx' / 'perps' / f'{inst_id}.{timeframe}.state.json'
    state_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)


def load_existing_wick_events(inst_id: str) -> Dict[str, WickEvent]:
    """Load existing wick events from wicks_events.jsonl."""
    events_file = VAULT_BASE / 'derived' / 'wicks' / 'okx' / 'perps' / inst_id / 'wicks_events.jsonl'
    
    if not events_file.exists():
        return {}
    
    events = {}
    
    with open(events_file, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            
            data = json.loads(line)
            wick = WickEvent(**data)
            
            # Keep latest status for each event_id
            events[wick.event_id] = wick
    
    logger.info(f"Loaded {len(events)} existing wick events for {inst_id}")
    return events


def write_wick_event(inst_id: str, wick: WickEvent):
    """Append wick event to wicks_events.jsonl."""
    events_file = VAULT_BASE / 'derived' / 'wicks' / 'okx' / 'perps' / inst_id / 'wicks_events.jsonl'
    events_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to dict
    wick_dict = {
        'event_id': wick.event_id,
        'instId': wick.instId,
        'timeframe': wick.timeframe,
        'creation_time_utc': wick.creation_time_utc,
        'window_end_utc': wick.window_end_utc,
        'wick_type': wick.wick_type,
        'wick_price': wick.wick_price,
        'wick_size': wick.wick_size,
        'body_size': wick.body_size,
        'candle_open': wick.candle_open,
        'candle_high': wick.candle_high,
        'candle_low': wick.candle_low,
        'candle_close': wick.candle_close,
        'status': wick.status,
        'touch_time_utc': wick.touch_time_utc,
        'age_at_touch_minutes': wick.age_at_touch_minutes,
        'touch_by_wick': wick.touch_by_wick,
        'touch_by_body': wick.touch_by_body,
        'touch_class': wick.touch_class,
        'tip_distance_ticks': wick.tip_distance_ticks,
        'tip_exact': wick.tip_exact,
        'tip_near': wick.tip_near,
        'signal_strength': wick.signal_strength,
        'tickSz': wick.tickSz,
        'tol_tip_ticks': wick.tol_tip_ticks
    }
    
    with open(events_file, 'a') as f:
        f.write(json.dumps(wick_dict) + '\n')


def write_wicks_state(inst_id: str, wicks: Dict[str, WickEvent]):
    """Write current state snapshot (one object per event_id, latest status)."""
    state_file = VAULT_BASE / 'derived' / 'wicks' / 'okx' / 'perps' / inst_id / 'wicks_state.json'
    state_file.parent.mkdir(parents=True, exist_ok=True)
    
    state_dict = {}
    
    for event_id, wick in wicks.items():
        state_dict[event_id] = {
            'event_id': wick.event_id,
            'instId': wick.instId,
            'timeframe': wick.timeframe,
            'creation_time_utc': wick.creation_time_utc,
            'wick_type': wick.wick_type,
            'wick_price': wick.wick_price,
            'wick_size': wick.wick_size,
            'status': wick.status,
            'touch_time_utc': wick.touch_time_utc,
            'age_at_touch_minutes': wick.age_at_touch_minutes,
            'touch_class': wick.touch_class,
            'tip_exact': wick.tip_exact,
            'tip_near': wick.tip_near,
            'signal_strength': wick.signal_strength
        }
    
    with open(state_file, 'w') as f:
        json.dump(state_dict, f, indent=2)



def check_wick_touch(wick: WickEvent, future_candle: Candle, tick_sz: Optional[Decimal]) -> Optional[Dict]:
    """
    Check if future candle touches wick (FROZEN RULES V1).
    Returns touch metadata if touched, None otherwise.
    """
    wick_price = Decimal(wick.wick_price)
    
    h = future_candle.high_decimal
    l = future_candle.low_decimal
    o = future_candle.open_decimal
    c = future_candle.close_decimal
    
    body_max = max(o, c)
    body_min = min(o, c)
    
    # Check wick touch
    touch_by_wick = False
    if wick.wick_type == 'high':
        touch_by_wick = (h >= wick_price)
    else:  # 'low'
        touch_by_wick = (l <= wick_price)
    
    # Check body touch
    touch_by_body = (body_min <= wick_price <= body_max)
    
    # If no touch at all, return None
    if not (touch_by_wick or touch_by_body):
        return None
    
    # Touch class
    if touch_by_body and touch_by_wick:
        touch_class = 'both'
    elif touch_by_body:
        touch_class = 'body'
    else:
        touch_class = 'wick'
    
    # Tip metrics (only when touch_by_wick AND tickSz available)
    tip_distance_ticks = None
    tip_exact = None
    tip_near = None
    signal_strength = None
    penetration_ticks = None
    
    if touch_by_wick and tick_sz is not None and tick_sz > 0:
        # Determine extremum
        if wick.wick_type == 'high':
            extremum = h
        else:  # 'low'
            extremum = l
        
        # Calculate tip distance
        tip_distance_abs = abs(extremum - wick_price)
        tip_distance_ticks = int(tip_distance_abs / tick_sz)  # Rounded down
        
        # Tip flags
        tip_exact = (tip_distance_ticks == 0)
        tip_near = (tip_distance_ticks >= 1 and tip_distance_ticks <= wick.tol_tip_ticks)
        
        # Signal strength
        if tip_exact:
            signal_strength = 'EXACT'
        elif tip_near:
            signal_strength = 'NEAR'
        elif tip_distance_ticks <= 3:
            signal_strength = 'CLOSE'
        else:
            signal_strength = 'TOUCHED'
        
        # Penetration ticks
        if wick.wick_type == 'high':
            penetration_ticks = int(max(Decimal('0'), extremum - wick_price) / tick_sz)
        else:  # 'low'
            penetration_ticks = int(max(Decimal('0'), wick_price - extremum) / tick_sz)
    
    # Calculate age at touch
    creation_time = datetime.fromisoformat(wick.creation_time_utc.replace('Z', '+00:00'))
    touch_time = datetime.fromisoformat(future_candle.window_end_utc.replace('Z', '+00:00'))
    age_minutes = int((touch_time - creation_time).total_seconds() / 60)
    
    return {
        'touch_time_utc': future_candle.window_end_utc,
        'age_at_touch_minutes': age_minutes,
        'touch_by_wick': touch_by_wick,
        'touch_by_body': touch_by_body,
        'touch_class': touch_class,
        'tip_distance_ticks': float(tip_distance_ticks) if tip_distance_ticks is not None else None,
        'tip_exact': tip_exact,
        'tip_near': tip_near,
        'signal_strength': signal_strength,
        'penetration_ticks': penetration_ticks
    }


def check_wick_expiry(wick: WickEvent, as_of_utc: datetime, expiry_hours: int = 168) -> bool:
    """
    Check if wick has expired (DETERMINISTIC).
    as_of_utc: Latest candle time, not wall-clock now.
    """
    creation_time = datetime.fromisoformat(wick.creation_time_utc.replace('Z', '+00:00'))
    age = as_of_utc - creation_time
    
    return age.total_seconds() / 3600 >= expiry_hours



def process_inst_id(inst_id: str):
    """
    Main processing loop (DETERMINISTIC + INCREMENTAL).
    
    For each timeframe:
    1. Load state cursor (last_processed_window_end_utc)
    2. Filter candles to NEW only (> last_processed)
    3. Detect new wicks in new candles
    4. Update existing untouched wicks using new candles
    5. Check expiry (deterministic as_of_utc from candles)
    6. Update state cursor to latest window_end
    """
    logger.info(f"Processing {inst_id}")
    
    # Load metadata
    try:
        metadata = load_metadata(inst_id)
        tick_sz_str = metadata.get('tickSz', '')
        
        # Parse tickSz (null-safe)
        tick_sz = None
        if tick_sz_str and tick_sz_str != '':
            try:
                tick_sz = Decimal(tick_sz_str)
                logger.info(f"Metadata loaded: tickSz={tick_sz}")
            except:
                logger.warning(f"Invalid tickSz: {tick_sz_str}, tip metrics will be null")
        else:
            logger.warning(f"No tickSz for {inst_id}, tip metrics will be null")
    
    except Exception as e:
        logger.error(f"BUILD_FAIL: Failed to load metadata for {inst_id}: {e}")
        return
    
    # Load trades (full history)
    trades = load_trades(inst_id)
    
    if not trades:
        logger.warning(f"No trades found for {inst_id}")
        return
    
    # Build candles (all timeframes)
    logger.info("Building candles...")
    candles_by_tf = build_all_timeframes(trades)
    
    for tf, candles in candles_by_tf.items():
        logger.info(f"Built {len(candles)} {tf} candles")
    
    # Load existing wick events (all timeframes)
    existing_wicks = load_existing_wick_events(inst_id)
    all_wicks = existing_wicks.copy()
    
    # Process each timeframe independently
    for tf in TIMEFRAMES:
        logger.info(f"\nProcessing timeframe: {tf}")
        
        candles = candles_by_tf[tf]
        
        if not candles:
            logger.info(f"No {tf} candles")
            continue
        
        # Sort candles by window_end_utc
        candles_sorted = sorted(candles, key=lambda c: c.window_end_utc)
        
        # Load state cursor for this timeframe
        state = load_timeframe_state(inst_id, tf)
        last_processed = state.get('last_processed_window_end_utc')
        
        # Filter to NEW candles only
        if last_processed:
            new_candles = [c for c in candles_sorted if c.window_end_utc > last_processed]
            logger.info(f"Incremental: {len(new_candles)} new candles (last processed: {last_processed})")
        else:
            new_candles = candles_sorted
            logger.info(f"First run: processing all {len(new_candles)} candles")
        
        if not new_candles:
            logger.info(f"No new {tf} candles to process")
            continue
        
        # Determine as_of_utc (latest candle time - DETERMINISTIC)
        as_of_utc = datetime.fromisoformat(new_candles[-1].window_end_utc.replace('Z', '+00:00'))
        
        # Track stats
        new_wicks_count = 0
        updated_wicks_count = 0
        expired_wicks_count = 0
        
        # STEP 1: Detect new wicks in new candles
        for candle in new_candles:
            wicks = detect_wicks(candle, str(tick_sz) if tick_sz else '0')
            
            for wick in wicks:
                if wick.event_id not in all_wicks:
                    all_wicks[wick.event_id] = wick
                    write_wick_event(inst_id, wick)
                    new_wicks_count += 1
        
        # STEP 2: Update existing untouched wicks (this timeframe only)
        tf_wicks = {eid: w for eid, w in all_wicks.items() if w.timeframe == tf}
        
        for event_id, wick in list(tf_wicks.items()):
            # Skip if already touched or expired
            if wick.status != 'untouched':
                continue
            
            # Check expiry first (deterministic)
            if check_wick_expiry(wick, as_of_utc, EXPIRY_HOURS):
                wick.status = 'expired'
                all_wicks[event_id] = wick  # Update in main dict
                write_wick_event(inst_id, wick)
                expired_wicks_count += 1
                continue
            
            # Check for touch in new candles
            creation_time = datetime.fromisoformat(wick.creation_time_utc.replace('Z', '+00:00'))
            
            for future_candle in new_candles:
                future_time = datetime.fromisoformat(future_candle.window_end_utc.replace('Z', '+00:00'))
                
                # Only check candles AFTER wick creation
                if future_time <= creation_time:
                    continue
                
                # Check touch
                touch_data = check_wick_touch(wick, future_candle, tick_sz)
                
                if touch_data:
                    # Update wick with touch data
                    wick.status = 'touched'
                    wick.touch_time_utc = touch_data['touch_time_utc']
                    wick.age_at_touch_minutes = touch_data['age_at_touch_minutes']
                    wick.touch_by_wick = touch_data['touch_by_wick']
                    wick.touch_by_body = touch_data['touch_by_body']
                    wick.touch_class = touch_data['touch_class']
                    wick.tip_distance_ticks = touch_data['tip_distance_ticks']
                    wick.tip_exact = touch_data['tip_exact']
                    wick.tip_near = touch_data['tip_near']
                    wick.signal_strength = touch_data['signal_strength']
                    
                    all_wicks[event_id] = wick  # Update in main dict
                    write_wick_event(inst_id, wick)
                    updated_wicks_count += 1
                    break  # Stop checking for this wick
        
        # Update state cursor to latest processed
        new_state = {
            'last_processed_window_end_utc': new_candles[-1].window_end_utc
        }
        save_timeframe_state(inst_id, tf, new_state)
        
        logger.info(f"{tf} complete: {new_wicks_count} new, {updated_wicks_count} updated, {expired_wicks_count} expired")
    
    # Write current state snapshot (all timeframes)
    write_wicks_state(inst_id, all_wicks)
    
    logger.info(f"\nProcessing complete for {inst_id}")
    logger.info(f"Total wicks tracked: {len(all_wicks)}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Untouched Wick Tracker (PATCHED)')
    parser.add_argument('--instId', required=True, help='Instrument ID (e.g., BTC-USDT-SWAP)')
    
    args = parser.parse_args()
    
    # Validate instrument
    if args.instId not in INSTRUMENTS:
        logger.error(f"BUILD_FAIL: Invalid instId: {args.instId} (allowed: {INSTRUMENTS})")
        return
    
    try:
        process_inst_id(args.instId)
    except Exception as e:
        logger.error(f"Error processing {args.instId}: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
