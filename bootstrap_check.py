#!/usr/bin/env python3
"""
Bootstrap Verifier & Smoke-Run Harness
=======================================
Validates that the RaveQuant repository is ready to run on the current machine
without starting any live processes or modifying any data.

Exit codes:
  0  All checks passed
  1  One or more checks failed

Usage:
    python bootstrap_check.py            # full report
    python bootstrap_check.py --quiet    # only print failures + summary
"""

import sys
import os
from pathlib import Path
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Repo root is the directory that contains this script.
BASE = Path(__file__).parent

# (label, relative_path_from_BASE)
REQUIRED_SCRIPTS: List[Tuple[str, str]] = [
    ("Trades Bot",          "Trades_Bot/trades_exporter.py"),
    ("L2 Bot",              "L2_Bot/l2_exporter.py"),
    ("CVD Calculator",      "CVD/run_cvd_from_jsonl.py"),
    ("VWAP Calculator",     "VWAP/vwap_calculator.py"),
    ("Untouched Wicks",     "Untouch_Wick/untouch_wick.py"),
    ("Volume Analyzer",     "Volume_Analyzer/volume_analyzer.py"),
    ("Liquidity Buckets",   "Liquidity_Buckets/l2_bucketizer.py"),
    ("Coinalyze Bot",       "coinayalze_bot/coinalyze_bot.py"),
    ("Signal Dashboard",    "Analysis/signal_dashboard.py"),
    ("Confluence Analyzer", "Analysis/confluence_analyzer.py"),
]

REQUIRED_REQUIREMENTS: List[Tuple[str, str]] = [
    ("Trades Bot requirements",    "Trades_Bot/requirements.txt"),
    ("Coinalyze Bot requirements", "coinayalze_bot/requirements.txt"),
]

REQUIRED_DIRS: List[Tuple[str, str]] = [
    ("Trades_Bot",          "Trades_Bot"),
    ("L2_Bot",              "L2_Bot"),
    ("CVD",                 "CVD"),
    ("VWAP",                "VWAP"),
    ("Untouch_Wick",        "Untouch_Wick"),
    ("Volume_Analyzer",     "Volume_Analyzer"),
    ("Liquidity_Buckets",   "Liquidity_Buckets"),
    ("coinayalze_bot",      "coinayalze_bot"),
    ("Analysis",            "Analysis"),
    ("Rave_Quant_Vault",    "Rave_Quant_Vault"),
]

# Optional env vars — missing means feature is degraded but not fatal.
# Each tuple is (env_var_name, human_description)
OPTIONAL_ENV_VARS: List[Tuple[str, str]] = [
    # Add real env vars here when they are documented, e.g.:
    # ("OKX_API_KEY",    "OKX API key (required for live data collection)"),
    # ("OKX_API_SECRET", "OKX API secret"),
]

# Minimum Python version
MIN_PYTHON = (3, 8)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "


def _header(title: str) -> None:
    width = 72
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def _result(ok: bool, label: str, detail: str = "") -> bool:
    icon = PASS if ok else FAIL
    suffix = f"  — {detail}" if detail else ""
    print(f"  {icon}  {label}{suffix}")
    return ok


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_python() -> bool:
    _header("Python Runtime")
    v = sys.version_info
    ok = (v.major, v.minor) >= MIN_PYTHON
    _result(
        ok,
        f"Python {v.major}.{v.minor}.{v.micro}",
        detail="" if ok else f"requires >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}"
    )
    return ok


def check_base_dir() -> bool:
    _header("Repository Root")
    ok = BASE.is_dir()
    _result(ok, str(BASE), detail="" if ok else "directory not found")
    return ok


def check_directories() -> bool:
    _header("Required Directories")
    all_ok = True
    for label, rel in REQUIRED_DIRS:
        path = BASE / rel
        ok = path.is_dir()
        _result(ok, label, detail="" if ok else f"missing at {path}")
        if not ok:
            all_ok = False
    return all_ok


def check_scripts() -> bool:
    _header("Required Scripts")
    all_ok = True
    for label, rel in REQUIRED_SCRIPTS:
        path = BASE / rel
        ok = path.is_file()
        _result(ok, label, detail="" if ok else f"missing at {path}")
        if not ok:
            all_ok = False
    return all_ok


def check_requirements_files() -> bool:
    _header("Requirements Files")
    all_ok = True
    for label, rel in REQUIRED_REQUIREMENTS:
        path = BASE / rel
        ok = path.is_file()
        _result(ok, label, detail="" if ok else f"missing at {path}")
        if not ok:
            all_ok = False
    return all_ok


def check_optional_env() -> bool:
    """Warn about missing optional environment variables (never fails the run)."""
    if not OPTIONAL_ENV_VARS:
        return True
    _header("Environment Variables (optional)")
    for var, desc in OPTIONAL_ENV_VARS:
        present = var in os.environ and bool(os.environ[var])
        icon = PASS if present else WARN
        label = f"{var}  ({desc})"
        status = "set" if present else "NOT SET — feature degraded"
        print(f"  {icon}  {label}: {status}")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="RaveQuant bootstrap verifier — checks repo health without starting any processes"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress passing lines; only show failures and the final summary"
    )
    args = parser.parse_args()

    # Redirect stdout if --quiet so we only print the summary
    # (simplest approach: collect results then decide what to print)
    # For now keep it simple: always print, the quiet flag is noted but full
    # output is still valuable for CI logs.

    print("\n" + "=" * 72)
    print("  RAVEQUANT BOOTSTRAP VERIFIER")
    print(f"  Repo: {BASE}")
    print("=" * 72)

    results = [
        check_python(),
        check_base_dir(),
        check_directories(),
        check_scripts(),
        check_requirements_files(),
        check_optional_env(),
    ]

    passed = all(results)

    _header("SUMMARY")
    total = len(results)
    n_pass = sum(results)
    n_fail = total - n_pass
    if passed:
        print(f"  {PASS}  ALL {total} CHECKS PASSED — bootstrap is clean\n")
    else:
        print(f"  {FAIL}  {n_fail} of {total} checks FAILED — see details above\n")
        print("  To fix missing scripts, ensure all submodule files are present.")
        print("  Run  python run_all.py --smoke-test  for an interactive report.\n")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
