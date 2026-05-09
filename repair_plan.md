# RaveQuant Repair Plan

## 1. Portability and Path Fixes
**Issue Identified:** The codebase heavily relied on hardcoded Windows paths (e.g., `C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault`). This caused the application to immediately fail (`P0` critical failure in `AUDIT_FINDINGS.txt`) when run in other environments (such as Linux servers or docker containers).

**Actions Taken:**
* Refactored `run_all.py` to calculate `RAVEQUANT_BASE` dynamically using `Path(__file__).resolve().parent`.
* Updated `CVD/run_cvd_from_jsonl.py`, `Volume_Analyzer/volume_analyzer.py`, `VWAP/vwap_calculator.py`, `Liquidity_Buckets/l2_bucketizer.py`, `Analysis/signal_dashboard.py`, `Analysis/confluence_analyzer.py`, `Untouch_Wick/untouch_wick.py`, `Untouch_Wick/find_signals.py`, and `Trades_Bot/trades_exporter.py` to dynamically resolve the `VAULT_BASE` via relative resolution: `Path(__file__).resolve().parent.parent / "Rave_Quant_Vault"`.
* Refactored `coinalyze_bot.py` and `confluence_analyzer.py` to correctly resolve their respective static paths in a platform-agnostic manner.

## 2. SyntaxWarnings and Errors Due to Invalid Escape Sequences
**Issue Identified:** Python 3.12+ enforces valid escape sequences strictly. Since the docstrings included Windows paths (e.g., `\o` or `\U`), it triggered syntax errors in files like `Analysis/confluence_analyzer.py`, `Volume_Analyzer/volume_analyzer.py` and `Trades_Bot/trades_exporter.py` failing compilation completely.

**Actions Taken:**
* Replaced normal docstrings (`"""`) with raw string literal docstrings (`r"""`) in `Analysis/confluence_analyzer.py`, `Volume_Analyzer/volume_analyzer.py` and `Trades_Bot/trades_exporter.py`. This resolves all `unicodeescape` decoding errors and escape sequence warnings without breaking the readable format of the path in the docstrings.

## 3. Configuration Refactoring (`P2` from `AUDIT_FINDINGS.txt`)
**Issue Identified:** `run_all.py` had hardcoded symbols (`['BTC-USDT-SWAP', 'ETH-USDT-SWAP']`). Adding a new coin required changing source code in the master runner, hindering extensibility.

**Actions Taken:**
* Updated `run_all.py` to optionally load symbols from a local `symbols.json` file.
* If `symbols.json` is not present, it safely falls back to the default `['BTC-USDT-SWAP', 'ETH-USDT-SWAP']` list to maintain backward compatibility.

## 4. Housekeeping
**Issue Identified:** Pre-compiled Python byte-code artifacts (`__pycache__/*.pyc`) were accidentally committed to the repository, polluting source control.
**Actions Taken:**
* Cleaned all `.pyc` and `__pycache__` artifacts from the git tracking index to ensure they are excluded from source commits.
