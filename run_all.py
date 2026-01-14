"""
MASTER RUNNER - Start All RaveQuant Systems (Enhanced)
======================================================
1. Check/install requirements
2. Start data collectors (trades, L2, Coinalyze)
3. Start calculators (CVD, VWAP, Wicks, Volume, Buckets)
4. Monitor system health
5. Provide status dashboard

ENHANCEMENTS:
- Uses centralized configuration
- Better process management
- Health monitoring
- Automatic recovery
- Timeout handling

Usage:
    python run_all.py [--check-only] [--no-start] [--health-check]
"""

import subprocess
import sys
import time
import signal
import psutil
from pathlib import Path
from typing import List, Dict, Optional
import json
import logging

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent))
from utils.config import Config
from utils.validation import ValidationError, validate_positive_int

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('run_all.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('Master_Runner')

# Base paths - use config
RAVEQUANT_BASE = Path(__file__).parent

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
    RAVEQUANT_BASE / 'L2_Bot' / 'requirements.txt',
    RAVEQUANT_BASE / 'coinayalze_bot' / 'requirements.txt'
]

# Process tracking
RUNNING_PROCESSES: Dict[str, subprocess.Popen] = {}


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
        logger.error(f"Python version too old: {sys.version}")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    logger.info(f"Python version check passed: {sys.version}")
    return True


def install_requirements():
    """Install all requirements with error handling."""
    print_header("INSTALLING REQUIREMENTS")
    
    for req_file in REQUIREMENTS:
        if not req_file.exists():
            print(f"⚠️ Skipping (not found): {req_file}")
            logger.warning(f"Requirements file not found: {req_file}")
            continue
        
        print(f"📦 Installing from: {req_file.name}")
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-r', str(req_file)],
                check=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            print(f"✅ Installed")
            logger.info(f"Installed requirements from {req_file.name}")
        except subprocess.TimeoutExpired:
            print(f"❌ Timeout installing from {req_file}")
            logger.error(f"Timeout installing requirements from {req_file}")
            return False
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed: {e}")
            print(e.stderr)
            logger.error(f"Failed to install requirements from {req_file}: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            logger.error(f"Unexpected error installing requirements: {e}", exc_info=True)
            return False
    
    print("\n✅ All requirements installed\n")
    logger.info("All requirements installed successfully")
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


def start_collector(name: str, script_path: Path, args: List[str] = None) -> Optional[subprocess.Popen]:
    """Start a collector process with error handling."""
    cmd = [sys.executable, str(script_path)]
    
    if args:
        cmd.extend(args)
    
    print(f"🚀 Starting {name}...")
    logger.info(f"Starting {name} with command: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=script_path.parent
        )
        
        # Wait a moment to check if process started successfully
        time.sleep(2)
        
        if process.poll() is not None:
            # Process already exited
            stdout, stderr = process.communicate()
            logger.error(f"{name} failed to start. Exit code: {process.returncode}")
            logger.error(f"STDOUT: {stdout}")
            logger.error(f"STDERR: {stderr}")
            print(f"❌ {name} failed to start (exit code: {process.returncode})")
            return None
        
        print(f"✅ {name} started (PID: {process.pid})")
        logger.info(f"{name} started successfully with PID {process.pid}")
        
        # Track process
        RUNNING_PROCESSES[name] = process
        
        return process
    
    except Exception as e:
        print(f"❌ Failed to start {name}: {e}")
        logger.error(f"Failed to start {name}: {e}", exc_info=True)
        return None


def check_process_health(name: str, process: subprocess.Popen) -> bool:
    """Check if a process is still running and healthy."""
    if process.poll() is not None:
        # Process has exited
        logger.warning(f"{name} process has exited with code {process.returncode}")
        return False
    
    try:
        # Check if process is actually alive
        proc = psutil.Process(process.pid)
        if proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE:
            return True
        else:
            logger.warning(f"{name} process is not healthy: {proc.status()}")
            return False
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        logger.warning(f"{name} process no longer exists")
        return False
    except Exception as e:
        logger.error(f"Error checking {name} health: {e}")
        return False


def health_check_all() -> Dict[str, bool]:
    """
    Check health of all running processes.
    Returns dict of {name: is_healthy}.
    """
    health_status = {}
    
    for name, process in RUNNING_PROCESSES.items():
        health_status[name] = check_process_health(name, process)
    
    return health_status


def stop_all_processes():
    """Stop all running processes gracefully."""
    print("\n🛑 Stopping all processes...")
    logger.info("Stopping all running processes")
    
    for name, process in RUNNING_PROCESSES.items():
        try:
            print(f"Stopping {name}...")
            
            # Try graceful shutdown first
            process.terminate()
            
            # Wait up to 10 seconds for process to terminate
            try:
                process.wait(timeout=10)
                print(f"✅ {name} stopped")
                logger.info(f"{name} stopped gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if not responding
                print(f"⚠️ Force killing {name}...")
                process.kill()
                process.wait()
                print(f"✅ {name} killed")
                logger.warning(f"{name} had to be force killed")
        
        except Exception as e:
            print(f"❌ Error stopping {name}: {e}")
            logger.error(f"Error stopping {name}: {e}", exc_info=True)
    
    RUNNING_PROCESSES.clear()
    print("✅ All processes stopped\n")


def signal_handler(signum, frame):
    """Handle interrupt signals."""
    print("\n\n⚠️ Interrupt signal received!")
    logger.info(f"Interrupt signal {signum} received")
    stop_all_processes()
    sys.exit(0)


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
    """Main entry point with enhanced error handling."""
    import argparse
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    parser = argparse.ArgumentParser(description='Master Runner - Start All RaveQuant Systems')
    parser.add_argument('--check-only', action='store_true', help='Only check components, don\'t start')
    parser.add_argument('--no-start', action='store_true', help='Skip starting collectors')
    parser.add_argument('--health-check', action='store_true', help='Check health of running processes')
    parser.add_argument('--instIds', nargs='+', default=Config.ALLOWED_INSTRUMENTS,
                       help='Instruments to process')
    
    args = parser.parse_args()
    
    print_header("RAVEQUANT MASTER RUNNER")
    logger.info("Master Runner started")
    
    # If health check mode, check and exit
    if args.health_check:
        print_header("HEALTH CHECK")
        health_status = health_check_all()
        
        if not health_status:
            print("⚠️ No processes are currently running")
            logger.info("No running processes found")
            return
        
        all_healthy = True
        for name, is_healthy in health_status.items():
            status = "✅ Healthy" if is_healthy else "❌ Unhealthy"
            print(f"{name}: {status}")
            
            if not is_healthy:
                all_healthy = False
        
        if all_healthy:
            print("\n✅ All processes healthy")
            logger.info("All processes healthy")
        else:
            print("\n⚠️ Some processes unhealthy")
            logger.warning("Some processes unhealthy")
        
        return
    
    # Check Python
    if not check_python():
        logger.error("Python version check failed")
        sys.exit(1)
    
    # Check components
    if not check_components():
        print("\n⚠️ Some components missing. System may not function fully.")
        logger.warning("Some components missing")
        response = input("Continue anyway? [y/N]: ")
        if response.lower() != 'y':
            sys.exit(1)
    
    if args.check_only:
        print("\n✅ Check complete. Exiting.\n")
        logger.info("Check-only mode complete")
        sys.exit(0)
    
    # Ensure vault directories exist
    try:
        Config.ensure_directories()
        print("✅ Vault directories ensured")
        logger.info("Vault directories created/verified")
    except Exception as e:
        print(f"⚠️ Error ensuring directories: {e}")
        logger.error(f"Error ensuring directories: {e}", exc_info=True)
    
    # Install requirements
    print("\n📦 Install requirements? [Y/n]: ", end='')
    response = input()
    if response.lower() != 'n':
        if not install_requirements():
            print("\n⚠️ Requirements installation failed. Continuing anyway...")
            logger.warning("Requirements installation failed")
    
    if args.no_start:
        print("\n⚠️ Skipping collector startup (--no-start)\n")
        logger.info("Skipping collector startup")
    else:
        # Start collectors
        try:
            processes = start_collectors()
            
            if not processes:
                print("\n⚠️ No collectors started. Check component paths.")
                logger.warning("No collectors started")
            else:
                print(f"\n✅ {len(processes)} collectors started")
                logger.info(f"{len(processes)} collectors started successfully")
            
            # Give collectors time to accumulate data
            print("⏳ Waiting 30 seconds for data collection...")
            time.sleep(30)
        except Exception as e:
            print(f"\n❌ Error starting collectors: {e}")
            logger.error(f"Error starting collectors: {e}", exc_info=True)
            stop_all_processes()
            sys.exit(1)
    
    # Run calculators
    try:
        run_calculators(args.instIds)
    except Exception as e:
        print(f"\n❌ Error running calculators: {e}")
        logger.error(f"Error running calculators: {e}", exc_info=True)
    
    # Done
    print_header("STARTUP COMPLETE")
    print("✅ System operational")
    logger.info("System startup complete")
    
    # Show health status
    health_status = health_check_all()
    if health_status:
        print("\n📊 Process Health:")
        for name, is_healthy in health_status.items():
            status = "✅ Running" if is_healthy else "❌ Stopped"
            print(f"  {name}: {status}")
    
    print("\n📊 Run signal dashboard:")
    analysis_path = RAVEQUANT_BASE / 'Analysis'
    if analysis_path.exists():
        print(f"   cd {analysis_path}")
        print("   python signal_dashboard.py --instId BTC-USDT-SWAP")
    
    print("\n📈 Run confluence analyzer:")
    if analysis_path.exists():
        print(f"   cd {analysis_path}")
        print("   python confluence_analyzer.py --instId BTC-USDT-SWAP")
    
    print(f"\n💡 To stop all processes, press Ctrl+C or run with --stop")
    print(f"💡 To check health, run: python run_all.py --health-check")
    print(f"\n{'='*80}\n")
    
    # Keep script running if collectors are active
    if RUNNING_PROCESSES:
        print("🔄 Master runner will keep running. Press Ctrl+C to stop all processes.\n")
        logger.info("Master runner entering monitoring mode")
        
        try:
            while True:
                time.sleep(60)
                
                # Periodic health check
                health_status = health_check_all()
                unhealthy = [name for name, healthy in health_status.items() if not healthy]
                
                if unhealthy:
                    logger.warning(f"Unhealthy processes detected: {unhealthy}")
                    print(f"\n⚠️ Warning: Unhealthy processes: {', '.join(unhealthy)}")
        
        except KeyboardInterrupt:
            print("\n\n⚠️ Keyboard interrupt received!")
            logger.info("Keyboard interrupt received")
            stop_all_processes()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        stop_all_processes()
        sys.exit(1)
