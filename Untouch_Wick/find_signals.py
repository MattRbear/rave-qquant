"""
Signal Finder - Your Edge Pattern Query
---------------------------------------
Find small wicks 20-40 min old, still untouched, surrounded by touched wicks.
These are your highest conviction setups - the "on the money" entries.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict
import argparse

# Paths
VAULT_BASE = Path(r"C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Signal_Finder')


def load_active_wicks(inst_id: str) -> Dict:
    """Load current active (untouched) wicks."""
    active_file = VAULT_BASE / 'derived' / 'wicks' / 'okx' / 'perps' / inst_id / 'wicks_active.json'
    
    if not active_file.exists():
        logger.warning(f"No active wicks file for {inst_id}")
        return {}
    
    with open(active_file, 'r') as f:
        return json.load(f)


def load_all_wick_events(inst_id: str) -> List[Dict]:
    """Load all wick events for context analysis."""
    events_file = VAULT_BASE / 'derived' / 'wicks' / 'okx' / 'perps' / inst_id / 'wicks_events.jsonl'
    
    if not events_file.exists():
        return []
    
    events = []
    with open(events_file, 'r') as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    
    return events


def get_surrounding_wicks(target_wick: Dict, all_events: List[Dict], 
                          window_minutes: int = 10) -> Dict:
    """
    Get wicks surrounding target wick (±window_minutes).
    Returns counts of touched vs untouched.
    """
    target_time = datetime.fromisoformat(target_wick['creation_time_utc'].replace('Z', '+00:00'))
    target_tf = target_wick['timeframe']
    
    start_time = target_time - timedelta(minutes=window_minutes)
    end_time = target_time + timedelta(minutes=window_minutes)
    
    surrounding = {
        'total': 0,
        'touched': 0,
        'untouched': 0,
        'expired': 0
    }
    
    for event in all_events:
        # Same timeframe only
        if event['timeframe'] != target_tf:
            continue
        
        # Skip self
        if event['event_id'] == target_wick['event_id']:
            continue
        
        event_time = datetime.fromisoformat(event['creation_time_utc'].replace('Z', '+00:00'))
        
        # Within window?
        if start_time <= event_time <= end_time:
            surrounding['total'] += 1
            
            if event['status'] == 'touched':
                surrounding['touched'] += 1
            elif event['status'] == 'untouched':
                surrounding['untouched'] += 1
            elif event['status'] == 'expired':
                surrounding['expired'] += 1
    
    return surrounding


def find_hidden_signals(inst_id: str, 
                        age_min: int = 20, 
                        age_max: int = 40,
                        timeframe: str = '1m',
                        min_touched_surrounding: int = 10) -> List[Dict]:
    """
    Find YOUR EDGE pattern:
    - Small wicks 20-40 min old
    - Still untouched
    - Surrounded by touched wicks (noise filter)
    - 1m timeframe (sweet spot)
    
    Returns list of high-conviction signals.
    """
    logger.info(f"Searching for hidden signals in {inst_id}...")
    logger.info(f"Age range: {age_min}-{age_max} minutes")
    logger.info(f"Timeframe: {timeframe}")
    
    # Load data
    active_wicks = load_active_wicks(inst_id)
    all_events = load_all_wick_events(inst_id)
    
    # Get untouched wicks for target timeframe
    tf_wicks = active_wicks.get(timeframe, [])
    
    if not tf_wicks:
        logger.warning(f"No untouched {timeframe} wicks for {inst_id}")
        return []
    
    logger.info(f"Found {len(tf_wicks)} untouched {timeframe} wicks")
    
    # Current time
    now = datetime.now(timezone.utc)
    
    signals = []
    
    for wick in tf_wicks:
        # Calculate age
        creation_time = datetime.fromisoformat(wick['creation_time_utc'].replace('Z', '+00:00'))
        age_minutes = (now - creation_time).total_seconds() / 60
        
        # Age filter
        if not (age_min <= age_minutes <= age_max):
            continue
        
        # Get surrounding context
        surrounding = get_surrounding_wicks(wick, all_events, window_minutes=10)
        
        # Filter: Must be surrounded by touched wicks (hidden signal)
        if surrounding['touched'] < min_touched_surrounding:
            continue
        
        # Calculate signal strength
        signal_strength = 'HIGH'
        if surrounding['touched'] >= 15:
            signal_strength = 'VERY_HIGH'
        
        signals.append({
            'wick': wick,
            'age_minutes': int(age_minutes),
            'surrounding': surrounding,
            'signal_strength': signal_strength,
            'instId': inst_id,
            'timeframe': timeframe
        })
    
    # Sort by signal strength (most touched surrounding first)
    signals.sort(key=lambda s: s['surrounding']['touched'], reverse=True)
    
    return signals


def print_signals(signals: List[Dict]):
    """Print signals in readable format."""
    if not signals:
        print("\n❌ NO SIGNALS FOUND")
        return
    
    print(f"\n{'='*80}")
    print(f"🎯 FOUND {len(signals)} HIDDEN SIGNALS - YOUR EDGE")
    print(f"{'='*80}\n")
    
    for i, sig in enumerate(signals, 1):
        wick = sig['wick']
        
        print(f"SIGNAL #{i} - {sig['signal_strength']}")
        print(f"  Instrument: {sig['instId']}")
        print(f"  Timeframe: {sig['timeframe']}")
        print(f"  Wick Type: {wick['wick_type'].upper()}")
        print(f"  Wick Price: {wick['wick_price']}")
        print(f"  Wick Size: {wick['wick_size']}")
        print(f"  Age: {sig['age_minutes']} minutes")
        print(f"  Created: {wick['creation_time_utc']}")
        print(f"\n  CONTEXT (±10 min):")
        print(f"    Total wicks: {sig['surrounding']['total']}")
        print(f"    Touched: {sig['surrounding']['touched']} ✓")
        print(f"    Untouched: {sig['surrounding']['untouched']}")
        print(f"    Expired: {sig['surrounding']['expired']}")
        print(f"\n  SETUP:")
        if wick['wick_type'] == 'high':
            print(f"    → SHORT from {wick['wick_price']} (fade down)")
        else:
            print(f"    → LONG from {wick['wick_price']} (fade up)")
        print(f"    → Stop: Beyond wick price (tight)")
        print(f"    → Target: Next untouched wick or body close through")
        print(f"\n{'-'*80}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Find Hidden Wick Signals')
    parser.add_argument('--instId', required=True, help='Instrument ID')
    parser.add_argument('--age-min', type=int, default=20, help='Min age in minutes (default: 20)')
    parser.add_argument('--age-max', type=int, default=40, help='Max age in minutes (default: 40)')
    parser.add_argument('--timeframe', default='1m', help='Timeframe (default: 1m)')
    parser.add_argument('--min-touched', type=int, default=10, help='Min touched surrounding (default: 10)')
    
    args = parser.parse_args()
    
    # Find signals
    signals = find_hidden_signals(
        args.instId,
        age_min=args.age_min,
        age_max=args.age_max,
        timeframe=args.timeframe,
        min_touched_surrounding=args.min_touched
    )
    
    # Print results
    print_signals(signals)
    
    # Summary
    if signals:
        print(f"✅ {len(signals)} high-conviction setups ready")
        print(f"🎯 Your edge: Small wicks hidden in noise, exact levels to hunt\n")


if __name__ == '__main__':
    main()
