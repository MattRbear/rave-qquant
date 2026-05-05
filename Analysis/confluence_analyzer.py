"""
CONFLUENCE ANALYZER - Multi-Layer Signal Detection
===================================================
Reads all data sources and identifies max conviction setups where:
- Untouched wick (your core edge)
- Volume tier T4 + absorption/divergence
- Liquidity bucket wall + imbalance
- CVD alignment
- VWAP confluence

Outputs ranked trade signals with conviction scores.

INPUT:
- Vault\\derived\\wicks\\okx\\perps\\{INSTID}\\wicks_events.jsonl
- Vault\\derived\\volume\\okx\\perps\\{INSTID}\\volume_1m.jsonl
- Vault\\derived\\liquidity_buckets\\okx\\perps\\{INSTID}\\{DATE}.jsonl
- Vault\\derived\\cvd\\okx\\perps\\{INSTID}\\cvd_1m.jsonl
- Vault\\derived\\vwap\\okx\\perps\\{INSTID}\\vwap_1m.jsonl

OUTPUT:
- ..\\Analysis\\confluence_signals.jsonl
"""

import json
import os
import logging
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from collections import defaultdict

# Paths
VAULT_BASE = Path(os.environ.get("RAVEQUANT_VAULT", Path(__file__).resolve().parent.parent / "Rave_Quant_Vault"))
OUTPUT_DIR = Path(os.environ.get("RAVEQUANT_ANALYSIS", Path(__file__).resolve().parent))

# Confluence thresholds
PRICE_TOLERANCE_PCT = Decimal('0.5')  # 0.5% = tight confluence
MAX_AGE_MINUTES = 60  # Only consider recent data

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Confluence_Analyzer')



def load_recent_wicks(inst_id: str, max_age_minutes: int = 60) -> List[Dict]:
    """Load recent untouched wicks."""
    wick_file = VAULT_BASE / 'derived' / 'wicks' / 'okx' / 'perps' / inst_id / 'wicks_events.jsonl'
    
    if not wick_file.exists():
        return []
    
    wicks = []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
    
    with open(wick_file, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            
            try:
                wick = json.loads(line)
                
                # Only untouched wicks
                if wick.get('status') != 'untouched':
                    continue
                
                # Check age
                created = datetime.fromisoformat(wick['creation_time_utc'].replace('Z', '+00:00'))
                if created < cutoff:
                    continue
                
                wicks.append(wick)
            
            except Exception as e:
                continue
    
    return wicks


def load_latest_volume(inst_id: str) -> Optional[Dict]:
    """Load latest volume metrics."""
    volume_file = VAULT_BASE / 'derived' / 'volume' / 'okx' / 'perps' / inst_id / 'volume_1m.jsonl'
    
    if not volume_file.exists():
        return None
    
    # Read last line
    try:
        with open(volume_file, 'r') as f:
            lines = f.readlines()
            if lines:
                return json.loads(lines[-1])
    except:
        pass
    
    return None


def load_latest_buckets(inst_id: str) -> Optional[Dict]:
    """Load latest liquidity bucket metrics."""
    # Try today's file
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    bucket_file = VAULT_BASE / 'derived' / 'liquidity_buckets' / 'okx' / 'perps' / inst_id / f'{today}.jsonl'
    
    if not bucket_file.exists():
        return None
    
    # Read last line
    try:
        with open(bucket_file, 'r') as f:
            lines = f.readlines()
            if lines:
                return json.loads(lines[-1])
    except:
        pass
    
    return None


def load_latest_cvd(inst_id: str) -> Optional[Dict]:
    """Load latest CVD."""
    cvd_file = VAULT_BASE / 'derived' / 'cvd' / 'okx' / 'perps' / inst_id / 'cvd_1m.jsonl'
    
    if not cvd_file.exists():
        return None
    
    # Read last line
    try:
        with open(cvd_file, 'r') as f:
            lines = f.readlines()
            if lines:
                return json.loads(lines[-1])
    except:
        pass
    
    return None


def load_latest_vwap(inst_id: str) -> Optional[Dict]:
    """Load latest VWAP."""
    vwap_file = VAULT_BASE / 'derived' / 'vwap' / 'okx' / 'perps' / inst_id / 'vwap_1m.jsonl'
    
    if not vwap_file.exists():
        return None
    
    # Read last line
    try:
        with open(vwap_file, 'r') as f:
            lines = f.readlines()
            if lines:
                return json.loads(lines[-1])
    except:
        pass
    
    return None



def prices_align(price1: Decimal, price2: Decimal, tolerance_pct: Decimal) -> bool:
    """Check if two prices are within tolerance."""
    if price2 == 0:
        return False
    
    distance_pct = abs((price1 - price2) / price2) * Decimal('100')
    return distance_pct <= tolerance_pct


def find_bucket_wall_at_price(buckets: Dict, target_price: Decimal, side: str) -> Optional[Dict]:
    """
    Check if there's a significant wall near target price.
    
    Returns: {band_idx, notional, imbalance, young_active, young_age_s}
    """
    if not buckets:
        return None
    
    mid_price = Decimal(buckets.get('mid_price', '0'))
    if mid_price == 0:
        return None
    
    # Check all bands for walls near target
    bands = buckets.get('bands_bps', [])
    
    if side == 'bid':
        notionals = buckets.get('bid_notional', [])
        imbalances = buckets.get('imbalance', [])
        young_active = buckets.get('bid_young_active', [])
        young_ages = buckets.get('bid_young_age_s', [])
    else:  # ask
        notionals = buckets.get('ask_notional', [])
        imbalances = buckets.get('imbalance', [])
        young_active = buckets.get('ask_young_active', [])
        young_ages = buckets.get('ask_young_age_s', [])
    
    # Calculate which band the target is in
    distance_bps = abs((target_price - mid_price) / mid_price) * Decimal('10000')
    
    for i, upper_bps in enumerate(bands):
        if distance_bps <= upper_bps:
            # Found the band
            if i < len(notionals):
                return {
                    'band_idx': i,
                    'band_bps': bands[i],
                    'notional': notionals[i],
                    'imbalance': imbalances[i] if i < len(imbalances) else '0',
                    'young_active': young_active[i] if i < len(young_active) else False,
                    'young_age_s': young_ages[i] if i < len(young_ages) else None
                }
    
    return None


def score_confluence(wick: Dict, volume: Optional[Dict], buckets: Optional[Dict],
                     cvd: Optional[Dict], vwap: Optional[Dict]) -> Dict:
    """
    Score confluence strength (0-100).
    
    Layers:
    - Wick (base): 20 points
    - Volume tier T4: +15
    - Absorption: +15
    - Bucket wall >1M: +15
    - Bucket imbalance >0.7: +10
    - Young wall (<5min): +10
    - CVD aligned: +10
    - VWAP confluence: +5
    """
    score = 20  # Base: untouched wick exists
    signals = ['WICK']
    
    wick_price = Decimal(wick['wick_price'])
    wick_type = wick['wick_type']
    
    # Volume signals
    if volume:
        if volume.get('volume_tier') == 'T4':
            score += 15
            signals.append('VOL_T4')
        
        if volume.get('absorption'):
            score += 15
            signals.append('ABSORPTION')
    
    # Bucket signals
    if buckets:
        side = 'ask' if wick_type == 'high' else 'bid'
        wall = find_bucket_wall_at_price(buckets, wick_price, side)
        
        if wall:
            notional = Decimal(wall['notional'])
            
            if notional > Decimal('1000000'):  # >1M
                score += 15
                signals.append(f"WALL_{notional/1000000:.1f}M")
            
            # Imbalance
            imb_str = wall['imbalance']
            if imb_str:
                imb = abs(Decimal(imb_str.replace('+', '').replace('%', '')))
                if imb > Decimal('0.7'):
                    score += 10
                    signals.append(f"IMB_{imb:.2f}")
            
            # Young wall
            if wall['young_active'] and wall['young_age_s'] and wall['young_age_s'] < 300:
                score += 10
                signals.append(f"YOUNG_{wall['young_age_s']}s")
    
    # CVD alignment
    if cvd:
        cvd_delta = Decimal(cvd.get('cvd_delta', '0'))
        
        # For high wick (resistance), want negative CVD (sellers)
        # For low wick (support), want positive CVD (buyers)
        if wick_type == 'high' and cvd_delta < 0:
            score += 10
            signals.append('CVD_ALIGNED')
        elif wick_type == 'low' and cvd_delta > 0:
            score += 10
            signals.append('CVD_ALIGNED')
    
    # VWAP confluence
    if vwap:
        vwap_session = Decimal(vwap.get('vwap_session', '0'))
        
        if vwap_session > 0:
            if prices_align(wick_price, vwap_session, PRICE_TOLERANCE_PCT):
                score += 5
                signals.append('VWAP_SESSION')
    
    return {
        'score': min(score, 100),
        'signals': signals,
        'signal_count': len(signals)
    }



def analyze_inst_id(inst_id: str):
    """
    Main analysis for one instrument.
    
    1. Load all recent data
    2. For each untouched wick, check confluence
    3. Score and rank signals
    4. Output top signals
    """
    logger.info(f"Analyzing {inst_id}...")
    
    # Load data
    wicks = load_recent_wicks(inst_id, MAX_AGE_MINUTES)
    volume = load_latest_volume(inst_id)
    buckets = load_latest_buckets(inst_id)
    cvd = load_latest_cvd(inst_id)
    vwap = load_latest_vwap(inst_id)
    
    logger.info(f"  Loaded: {len(wicks)} wicks, volume={'✓' if volume else '✗'}, buckets={'✓' if buckets else '✗'}")
    
    if not wicks:
        logger.info(f"  No recent untouched wicks found")
        return []
    
    # Analyze each wick
    signals = []
    
    for wick in wicks:
        confluence = score_confluence(wick, volume, buckets, cvd, vwap)
        
        # Only keep signals with score >= 50
        if confluence['score'] >= 50:
            signal = {
                'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                'instId': inst_id,
                'wick_price': wick['wick_price'],
                'wick_type': wick['wick_type'],
                'wick_age_minutes': wick.get('age_minutes', 0),
                'timeframe': wick['timeframe'],
                'confluence_score': confluence['score'],
                'signals': confluence['signals'],
                'signal_count': confluence['signal_count'],
                'direction': 'SHORT' if wick['wick_type'] == 'high' else 'LONG',
                'entry_price': wick['wick_price'],
                'stop_price': None  # Can calculate from wick + buffer
            }
            
            signals.append(signal)
    
    # Sort by score (descending)
    signals.sort(key=lambda s: s['confluence_score'], reverse=True)
    
    return signals


def write_signals(signals: List[Dict]):
    """Write signals to output file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    output_file = OUTPUT_DIR / 'confluence_signals.jsonl'
    
    # Clear old file
    if output_file.exists():
        output_file.unlink()
    
    # Write new signals
    with open(output_file, 'w') as f:
        for signal in signals:
            f.write(json.dumps(signal) + '\n')
    
    logger.info(f"Wrote {len(signals)} signals to {output_file}")


def print_signals(signals: List[Dict]):
    """Print signals to console."""
    if not signals:
        print("\n✅ No high-conviction signals found")
        return
    
    print(f"\n{'='*80}")
    print(f" MAX CONVICTION SIGNALS ({len(signals)} found)")
    print(f"{'='*80}")
    
    for i, sig in enumerate(signals, 1):
        print(f"\n#{i} | Score: {sig['confluence_score']}/100 | {sig['direction']} @ {sig['entry_price']}")
        print(f"    Wick: {sig['wick_type']} on {sig['timeframe']} (age: {sig['wick_age_minutes']}min)")
        print(f"    Signals: {', '.join(sig['signals'])}")
        print(f"    Layers: {sig['signal_count']}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Confluence Analyzer - Multi-Layer Signal Detection')
    parser.add_argument('--instId', default='BTC-USDT-SWAP', help='Instrument ID')
    
    args = parser.parse_args()
    
    print(f"\n{'='*80}")
    print(" CONFLUENCE ANALYZER - MULTI-LAYER SIGNAL DETECTION")
    print(f"{'='*80}")
    print(f"\nAnalyzing: {args.instId}")
    print(f"Max age: {MAX_AGE_MINUTES} minutes")
    print(f"Price tolerance: {PRICE_TOLERANCE_PCT}%")
    
    # Analyze
    signals = analyze_inst_id(args.instId)
    
    # Output
    write_signals(signals)
    print_signals(signals)
    
    print(f"\n{'='*80}")
    print(" ANALYSIS COMPLETE")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
