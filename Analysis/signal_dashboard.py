"""
SIGNAL DASHBOARD - Real-Time System Status
===========================================
Shows current state of all metrics:
- Untouched wicks count
- Volume tier + absorption
- Liquidity bucket walls
- CVD direction
- VWAP levels
- Coinalyze data
- Data freshness

Quick health check for trading readiness.

OUTPUT: Console display (no file output)
"""

import os
import json
import logging
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

# Paths
VAULT_BASE = Path(os.environ.get("RAVE_VAULT_BASE", Path(__file__).resolve().parent.parent / "Rave_Quant_Vault"))

# Freshness thresholds
MAX_AGE_MINUTES = 15  # Data older than 15min = stale

logging.basicConfig(level=logging.WARNING)  # Quiet


def get_file_age(filepath: Path) -> Optional[int]:
    """Get file age in minutes."""
    if not filepath.exists():
        return None
    
    mtime = datetime.fromtimestamp(filepath.stat().st_mtime, tz=timezone.utc)
    age = (datetime.now(timezone.utc) - mtime).total_seconds() / 60
    return int(age)


def load_last_line(filepath: Path) -> Optional[Dict]:
    """Load last line from JSONL file."""
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
            if lines:
                return json.loads(lines[-1])
    except:
        pass
    
    return None


def get_wick_status(inst_id: str) -> Dict:
    """Get untouched wick status."""
    wick_file = VAULT_BASE / 'derived' / 'wicks' / 'okx' / 'perps' / inst_id / 'wicks_events.jsonl'
    
    if not wick_file.exists():
        return {'status': 'MISSING', 'count': 0}
    
    count = 0
    recent = 0
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=60)
    
    try:
        with open(wick_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                
                try:
                    wick = json.loads(line)
                    if wick.get('status') == 'untouched':
                        count += 1
                        
                        created = datetime.fromisoformat(wick['creation_time_utc'].replace('Z', '+00:00'))
                        if created >= cutoff:
                            recent += 1
                except:
                    continue
    except:
        return {'status': 'ERROR', 'count': 0}
    
    age = get_file_age(wick_file)
    
    return {
        'status': 'FRESH' if age and age < MAX_AGE_MINUTES else 'STALE',
        'count': count,
        'recent': recent,
        'age_min': age
    }


def get_volume_status(inst_id: str) -> Dict:
    """Get latest volume metrics."""
    volume_file = VAULT_BASE / 'derived' / 'volume' / 'okx' / 'perps' / inst_id / 'volume_1m.jsonl'
    
    vol = load_last_line(volume_file)
    age = get_file_age(volume_file)
    
    if not vol:
        return {'status': 'MISSING'}
    
    return {
        'status': 'FRESH' if age and age < MAX_AGE_MINUTES else 'STALE',
        'tier': vol.get('volume_tier', 'UNKNOWN'),
        'absorption': vol.get('absorption', False),
        'divergence': vol.get('divergence', False),
        'age_min': age
    }


def get_bucket_status(inst_id: str) -> Dict:
    """Get latest bucket metrics."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    bucket_file = VAULT_BASE / 'derived' / 'liquidity_buckets' / 'okx' / 'perps' / inst_id / f'{today}.jsonl'
    
    bucket = load_last_line(bucket_file)
    age = get_file_age(bucket_file)
    
    if not bucket:
        return {'status': 'MISSING'}
    
    # Count young walls
    young_bid = sum(1 for active in bucket.get('bid_young_active', []) if active)
    young_ask = sum(1 for active in bucket.get('ask_young_active', []) if active)
    
    return {
        'status': 'FRESH' if age and age < MAX_AGE_MINUTES else 'STALE',
        'young_bid_walls': young_bid,
        'young_ask_walls': young_ask,
        'age_min': age
    }


def get_cvd_status(inst_id: str) -> Dict:
    """Get latest CVD."""
    cvd_file = VAULT_BASE / 'derived' / 'cvd' / 'okx' / 'perps' / inst_id / 'cvd_1m.jsonl'
    
    cvd = load_last_line(cvd_file)
    age = get_file_age(cvd_file)
    
    if not cvd:
        return {'status': 'MISSING'}
    
    delta = Decimal(cvd.get('cvd_delta', '0'))
    direction = 'BULLISH' if delta > 0 else 'BEARISH' if delta < 0 else 'NEUTRAL'
    
    return {
        'status': 'FRESH' if age and age < MAX_AGE_MINUTES else 'STALE',
        'delta': str(delta),
        'direction': direction,
        'age_min': age
    }


def get_vwap_status(inst_id: str) -> Dict:
    """Get latest VWAP."""
    vwap_file = VAULT_BASE / 'derived' / 'vwap' / 'okx' / 'perps' / inst_id / 'vwap_1m.jsonl'
    
    vwap = load_last_line(vwap_file)
    age = get_file_age(vwap_file)
    
    if not vwap:
        return {'status': 'MISSING'}
    
    return {
        'status': 'FRESH' if age and age < MAX_AGE_MINUTES else 'STALE',
        'vwap_1h': vwap.get('vwap_1h'),
        'vwap_session': vwap.get('vwap_session'),
        'age_min': age
    }


def print_dashboard(inst_id: str):
    """Print complete dashboard."""
    print(f"\n{'='*80}")
    print(f" SIGNAL DASHBOARD - {inst_id}")
    print(f"{'='*80}")
    print(f" Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*80}\n")
    
    # Wicks
    wicks = get_wick_status(inst_id)
    emoji = '✅' if wicks['status'] == 'FRESH' else '⚠️' if wicks['status'] == 'STALE' else '❌'
    print(f"{emoji} UNTOUCHED WICKS: {wicks.get('status', 'UNKNOWN')}")
    if 'count' in wicks:
        print(f"   Total: {wicks['count']} | Recent (1h): {wicks.get('recent', 0)}")
        if wicks.get('age_min'):
            print(f"   Age: {wicks['age_min']} minutes")
    print()
    
    # Volume
    volume = get_volume_status(inst_id)
    emoji = '✅' if volume['status'] == 'FRESH' else '⚠️' if volume['status'] == 'STALE' else '❌'
    print(f"{emoji} VOLUME: {volume.get('status', 'UNKNOWN')}")
    if 'tier' in volume:
        tier_emoji = {'T1': '⚪', 'T2': '🟢', 'T3': '🟡', 'T4': '🔴'}.get(volume['tier'], '❓')
        print(f"   Tier: {tier_emoji} {volume['tier']}")
        print(f"   Absorption: {'🚨 YES' if volume['absorption'] else 'No'}")
        print(f"   Divergence: {'🚨 YES' if volume['divergence'] else 'No'}")
        if volume.get('age_min'):
            print(f"   Age: {volume['age_min']} minutes")
    print()
    
    # Buckets
    buckets = get_bucket_status(inst_id)
    emoji = '✅' if buckets['status'] == 'FRESH' else '⚠️' if buckets['status'] == 'STALE' else '❌'
    print(f"{emoji} LIQUIDITY BUCKETS: {buckets.get('status', 'UNKNOWN')}")
    if 'young_bid_walls' in buckets:
        print(f"   Young Bid Walls: {buckets['young_bid_walls']}")
        print(f"   Young Ask Walls: {buckets['young_ask_walls']}")
        if buckets.get('age_min'):
            print(f"   Age: {buckets['age_min']} minutes")
    print()
    
    # CVD
    cvd = get_cvd_status(inst_id)
    emoji = '✅' if cvd['status'] == 'FRESH' else '⚠️' if cvd['status'] == 'STALE' else '❌'
    print(f"{emoji} CVD: {cvd.get('status', 'UNKNOWN')}")
    if 'direction' in cvd:
        dir_emoji = '🐂' if cvd['direction'] == 'BULLISH' else '🐻' if cvd['direction'] == 'BEARISH' else '➖'
        print(f"   Direction: {dir_emoji} {cvd['direction']}")
        print(f"   Delta: {cvd['delta']}")
        if cvd.get('age_min'):
            print(f"   Age: {cvd['age_min']} minutes")
    print()
    
    # VWAP
    vwap = get_vwap_status(inst_id)
    emoji = '✅' if vwap['status'] == 'FRESH' else '⚠️' if vwap['status'] == 'STALE' else '❌'
    print(f"{emoji} VWAP: {vwap.get('status', 'UNKNOWN')}")
    if 'vwap_1h' in vwap:
        print(f"   1H: {vwap['vwap_1h']}")
        print(f"   Session: {vwap['vwap_session']}")
        if vwap.get('age_min'):
            print(f"   Age: {vwap['age_min']} minutes")
    print()
    
    # Overall health
    statuses = [wicks['status'], volume['status'], buckets['status'], cvd['status'], vwap['status']]
    fresh_count = sum(1 for s in statuses if s == 'FRESH')
    missing_count = sum(1 for s in statuses if s == 'MISSING')
    
    print(f"{'='*80}")
    print(" SYSTEM HEALTH")
    print(f"{'='*80}")
    
    if missing_count == 0 and fresh_count == 5:
        print("✅ ALL SYSTEMS OPERATIONAL")
    elif missing_count > 0:
        print(f"⚠️ {missing_count} COMPONENTS MISSING")
    elif fresh_count < 5:
        print(f"⚠️ {5 - fresh_count} COMPONENTS STALE")
    
    print(f"\n{'='*80}\n")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Signal Dashboard - System Status')
    parser.add_argument('--instId', default='BTC-USDT-SWAP', help='Instrument ID')
    
    args = parser.parse_args()
    
    print_dashboard(args.instId)


if __name__ == '__main__':
    main()
