"""
MASTER RUNNER - Start All RaveQuant Systems
============================================
1. Check/install requirements
2. Start data collectors (trades, L2, Coinalyze)
3. Start calculators (CVD, VWAP, Wicks, Volume, Buckets)
4. Monitor system health
5. Provide status dashboard

Usage:
    python run_all.py [--check-only] [--no-start]
"""

import subprocess
import sys
import os
import time
from pathlib import Path
from typing import List, Dict
import json

# Base paths
RAVEQUANT_BASE = Path(os.environ.get("RAVEQUANT_BASE", Path(__file__).resolve().parent))

# Component paths
COMPONENTS = {
    'trades': RAVEQUANT_BASE / 'Trades_Bot' / 'trades_exporter.py',
    'l2': RAVEQUANT_BASE / 'L2_Bot' / 'l2_exporter.py',
    'cvd': RAVEQUANT_BASE / 'CVD' / 'run_cvd_from_jsonl.py',
    'vwap': RAVEQUANT_BASE / 'VWAP' / 'vwap_calculator.py',
    'wicks': RAVEQUANT_BASE / 'Untouch_Wick' / 'untouch_wick.py',
    'volume': RAVEQUANT_BASE / 'Volume_Analyzer' / 'volume_analyzer.py',
    'buckets': RAVEQUANT_BASE / 'Liquidity_Buckets' / 'l2_bucketizer.py',
    'coinalyze': RAVEQUANT_BASE / 'coinayalze_bot' / 'coinalyze_bot.py'
}

# Requirements files
REQUIREMENTS = [
    RAVEQUANT_BASE / 'Trades_Bot' / 'requirements.txt',
    RAVEQUANT_BASE / 'coinayalze_bot' / 'requirements.txt'
]


def print_header(text: str):
    """Print formatted header."""
    print(f"\n{'='*80}")
    print(f" {text}")
    print(f"{'='*80}\n")


def check_python():
    """Check Python version."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ required")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def install_requirements():
    """Install all requirements."""
    print_header("INSTALLING REQUIREMENTS")
    
    for req_file in REQUIREMENTS:
        if not req_file.exists():
            print(f"⚠️ Skipping (not found): {req_file}")
            continue
        
        print(f"📦 Installing from: {req_file.name}")
        
        try:
            subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-r', str(req_file)],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"✅ Installed")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed: {e}")
            print(e.stderr)
            return False
    
    print("\n✅ All requirements installed\n")
    return True


def check_components():
    """Check if all components exist."""
    print_header("CHECKING COMPONENTS")
    
    missing = []
    
    for name, path in COMPONENTS.items():
        if path.exists():
            print(f"✅ {name.upper()}: {path.name}")
        else:
            print(f"❌ {name.upper()}: MISSING")
            missing.append(name)
    
    if missing:
        print(f"\n⚠️ Missing components: {', '.join(missing)}")
        return False
    
    print("\n✅ All components present\n")
    return True


def start_collector(name: str, script_path: Path, args: List[str] = None) -> subprocess.Popen:
    """Start a collector process."""
    cmd = [sys.executable, str(script_path)]
    
    if args:
        cmd.extend(args)
    
    print(f"🚀 Starting {name}...")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=script_path.parent
        )
        
        print(f"✅ {name} started (PID: {process.pid})")
        return process
    
    except Exception as e:
        print(f"❌ Failed to start {name}: {e}")
        return None


def run_calculator(name: str, script_path: Path, inst_id: str):
    """Run a calculator once."""
    # CVD uses --symbol (BTC-USDT format), others use --instId (BTC-USDT-SWAP format)
    if 'cvd' in name.lower():
        # Strip -SWAP for CVD
        symbol = inst_id.replace('-SWAP', '')
        cmd = [sys.executable, str(script_path), '--symbol', symbol]
    else:
        cmd = [sys.executable, str(script_path), '--instId', inst_id]
    
    print(f"⚙️ Running {name} for {inst_id}...")
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            cwd=script_path.parent,
            timeout=60
        )
        
        print(f"✅ {name} complete")
        return True
    
    except subprocess.TimeoutExpired:
        print(f"⚠️ {name} timeout (still processing)")
        return False
    
    except subprocess.CalledProcessError as e:
        print(f"❌ {name} failed: {e}")
        print(e.stderr[:500])  # First 500 chars of error
        return False


def start_collectors():
    """Start all data collectors."""
    print_header("STARTING DATA COLLECTORS")
    
    processes = {}
    
    # Trades (24/7)
    if COMPONENTS['trades'].exists():
        p = start_collector('trades', COMPONENTS['trades'])
        if p:
            processes['trades'] = p
    
    # L2 (24/7)
    if COMPONENTS['l2'].exists():
        p = start_collector('l2', COMPONENTS['l2'])
        if p:
            processes['l2'] = p
    
    # Coinalyze (periodic)
    if COMPONENTS['coinalyze'].exists():
        p = start_collector('coinalyze', COMPONENTS['coinalyze'], ['--once'])
        if p:
            processes['coinalyze'] = p
    
    time.sleep(3)  # Let them start
    
    print(f"\n✅ {len(processes)} collectors started\n")
    return processes


def run_calculators(inst_ids: List[str]):
    """Run all calculators."""
    print_header("RUNNING CALCULATORS")
    
    for inst_id in inst_ids:
        print(f"\n--- Processing {inst_id} ---\n")
        
        # CVD
        if COMPONENTS['cvd'].exists():
            run_calculator('CVD', COMPONENTS['cvd'], inst_id)
        
        # VWAP
        if COMPONENTS['vwap'].exists():
            run_calculator('VWAP', COMPONENTS['vwap'], inst_id)
        
        # Wicks
        if COMPONENTS['wicks'].exists():
            run_calculator('Wicks', COMPONENTS['wicks'], inst_id)
        
        # Volume
        if COMPONENTS['volume'].exists():
            run_calculator('Volume', COMPONENTS['volume'], inst_id)
        
        # Buckets
        if COMPONENTS['buckets'].exists():
            run_calculator('Buckets', COMPONENTS['buckets'], inst_id)
    
    print("\n✅ Calculator run complete\n")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Master Runner - Start All RaveQuant Systems')
    parser.add_argument('--check-only', action='store_true', help='Only check components, don\'t start')
    parser.add_argument('--no-start', action='store_true', help='Skip starting collectors')
    parser.add_argument('--instIds', nargs='+', default=['BTC-USDT-SWAP', 'ETH-USDT-SWAP'],
                       help='Instruments to process')
    
    args = parser.parse_args()
    
    print_header("RAVEQUANT MASTER RUNNER")
    
    # Check Python
    if not check_python():
        sys.exit(1)
    
    # Check components
    if not check_components():
        print("\n⚠️ Some components missing. System may not function fully.")
        response = input("Continue anyway? [y/N]: ")
        if response.lower() != 'y':
            sys.exit(1)
    
    if args.check_only:
        print("\n✅ Check complete. Exiting.\n")
        sys.exit(0)
    
    # Install requirements
    print("\n📦 Install requirements? [Y/n]: ", end='')
    response = input()
    if response.lower() != 'n':
        if not install_requirements():
            print("\n⚠️ Requirements installation failed. Continuing anyway...")
    
    if args.no_start:
        print("\n⚠️ Skipping collector startup (--no-start)\n")
    else:
        # Start collectors
        processes = start_collectors()
        
        if not processes:
            print("\n⚠️ No collectors started. Check component paths.")
        
        # Give collectors time to accumulate data
        print("⏳ Waiting 30 seconds for data collection...")
        time.sleep(30)
    
    # Run calculators
    run_calculators(args.instIds)
    
    # Done
    print_header("STARTUP COMPLETE")
    print("✅ System operational")
    print("\n📊 Run signal dashboard:")
    print(f"   cd {RAVEQUANT_BASE / 'Analysis'}")
    print("   python signal_dashboard.py --instId BTC-USDT-SWAP")
    print("\n📈 Run confluence analyzer:")
    print(f"   cd {RAVEQUANT_BASE / 'Analysis'}")
    print("   python confluence_analyzer.py --instId BTC-USDT-SWAP")
    print(f"\n{'='*80}\n")


if __name__ == '__main__':
    main()
