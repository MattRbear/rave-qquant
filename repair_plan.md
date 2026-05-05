# Repair Plan: Refactoring Hardcoded Windows Paths

## Issue Overview
The codebase contained several instances of hardcoded, absolute Windows file paths (e.g., `C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault`).
1. These paths are not portable and break the application on Linux, Mac, or any machine with a different user directory.
2. In docstrings and standard strings, raw strings were sometimes missing, resulting in `SyntaxWarning: invalid escape sequence '\o'` or `SyntaxError: (unicode error) 'unicodeescape' codec can't decode bytes...` because of the `\U` in `C:\Users`.

## Adjustments Made

### 1. Removing Hardcoded `C:\Users` Paths
We replaced absolute Windows paths with relative `pathlib.Path` structures using `os.environ` to allow easy overriding, falling back dynamically to relative paths using `__file__`.

Modified Files:
- `run_all.py`
- `CVD/run_cvd_from_jsonl.py`
- `Volume_Analyzer/volume_analyzer.py`
- `VWAP/vwap_calculator.py`
- `Liquidity_Buckets/l2_bucketizer.py`
- `Analysis/signal_dashboard.py`
- `Analysis/confluence_analyzer.py`
- `coinayalze_bot/coinalyze_bot.py`
- `Untouch_Wick/untouch_wick.py`
- `Untouch_Wick/find_signals.py`
- `Trades_Bot/trades_exporter.py`

*Example change:*
```python
# Before
VAULT_BASE = Path(r"C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault")

# After
import os
VAULT_BASE = Path(os.environ.get("RAVEQUANT_VAULT", Path(__file__).resolve().parent.parent / "Rave_Quant_Vault"))
```

### 2. Fixing Escape Sequences in Docstrings
Python 3.12+ treats invalid escape sequences as warnings/errors. We converted single backslashes in docstrings specifying paths to double backslashes.

Modified Files:
- `Volume_Analyzer/volume_analyzer.py`
- `Analysis/confluence_analyzer.py`
- `Trades_Bot/trades_exporter.py`

*Example change:*
```python
# Before
INPUT: Vault\raw\okx\trades_perps\{INSTID}\{DATE}.jsonl

# After
INPUT: Vault\\raw\\okx\\trades_perps\\{INSTID}\\{DATE}.jsonl
```

### 3. Verification
Executed codebase-wide compilation to verify all syntax errors have been resolved:
`find . -name "*.py" -exec python -m py_compile {} +`

The output is now clean with zero compilation or escape sequence errors.
