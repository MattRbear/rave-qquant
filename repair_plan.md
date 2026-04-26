# RaveQuant Repair Plan

## Issues Discovered
1. **Critical Path Failures**: The entire system previously relied on hardcoded absolute paths specifically mapping to `C:\Users\M.R Bear\Documents\RaveQuant...`, meaning no scripts could run successfully without crashing when executed dynamically.
2. **Configuration Bottlenecks**: The symbol lists were hardcoded across multiple scripts, meaning adding a single symbol like `SOL-USDT-SWAP` required modifications in multiple source files.
3. **VWAP Deduplication Bottlenecks**: The `vwap_calculator.py` performed an O(N^2) operation because it was reading from the output file directly on every write operation, drastically slowing down data analysis.
4. **Trades_Bot Inefficiencies & Data Reliability**:
   - `Trades_Bot` was subject to data loss during downtime since it lacked a backfill feature.
   - It also suffered from N+1 I/O bottlenecks because files were opened and closed for every single incoming WebSocket message.
   - Using standard `json` in tight high-frequency WebSocket streams was slower than necessary.

## Adjustments Made
1. **Path Agnostic Architecture**: Added dynamic path resolutions falling back onto `os.environ` environment variables (`RAVEQUANT_BASE`, `RAVEQUANT_VAULT`), while resolving to the source repository paths (`Path(__file__).resolve()`) dynamically.
2. **Centralized Configuration**: Added a centralized `config.json` configuration file at the repository root to easily control target instruments like `["BTC-USDT-SWAP", "ETH-USDT-SWAP"]`, and dynamically loaded them into `Trades_Bot`.
3. **VWAP Performance Optimization**: Implemented an in-memory O(1) deduplication check using a Python `set()` across string-extracted `window_start_utc` keys, effectively eliminating the massive O(N^2) overhead.
4. **Trades_Bot Overhaul**:
   - Swapped `json` with `orjson` for fast decoding streams.
   - Implemented an `aiohttp` based historical backfill initialization stage targeting `history-trades` on the OKX REST API.
   - Centralized all `open()` file requests into a cached dictionary of handles, enabling `.flush()` output buffering natively without constantly closing and rewriting handles.
5. **Testing & Integrity Assurance**: Added testing suites verifying VWAP logic (`tests/test_vwap.py`) directly from root using `pytest`.
