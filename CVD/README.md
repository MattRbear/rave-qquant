# CVD CALCULATOR - JSONL MODE

**Cumulative Volume Delta calculation from raw trade data (no SQL)**

---

## MISSION

Calculate CVD (Cumulative Volume Delta) from OKX trade stream:
- Read raw trades from vault JSONL files
- Process in strict chronological order
- Maintain running CVD (buy adds, sell subtracts)
- Output 1m resolution to vault
- Higher timeframes (5m/15m/1h/4h/1d) derived later via snapshot

---

## ARCHITECTURE

```
Vault\raw\okx\trades\{SYMBOL}\YYYY-MM-DD.jsonl
         ↓
  [CVD Calculator]
    ├─ Load state (last_ts, last_id, last_cvd)
    ├─ Parse new trades only
    ├─ Sort by (timestamp, trade_id)
    ├─ Calculate CVD:
    │    buy → cvd += size_usd
    │    sell → cvd -= size_usd
    ├─ Aggregate to 1m windows
    └─ Write outputs
         ↓
Vault\derived\cvd\okx\{SYMBOL}\1m\YYYY-MM-DD.jsonl
Vault\state\cvd\okx\{SYMBOL}.state.json
```

---

## CVD STRATEGY

### 1m Resolution (Ground Truth)
- Every trade processed
- CVD updated continuously
- Bucketed into 1m windows
- Last CVD value in window = window CVD

### Higher Timeframes (Derived)
CVD for HTF = snapshot at window close:
- **5m CVD** = CVD from 1m candle at minutes :04, :09, :14, etc.
- **15m CVD** = CVD from 1m candle at minutes :14, :29, :44, :59
- **1h CVD** = CVD from 1m candle at minute :59
- **4h CVD** = CVD from 1m candle at 03:59, 07:59, 11:59, etc.
- **1d CVD** = CVD from 1m candle at 23:59 UTC

**Why this works:** CVD is cumulative. The value at period end IS the period value.

---

## FILE FORMATS

### Input: Raw Trades
```json
{
  "exchange": "okx",
  "symbol": "BTC/USDT",
  "trade_id": "123456",
  "timestamp_utc": "2023-12-14T15:30:45.123Z",
  "price": "43250.5",
  "size": "0.5",
  "side": "buy"
}
```

### Output: 1m CVD
```json
{
  "window_start_utc": "2023-12-14T15:30:00Z",
  "cvd_value": "1234567.89",
  "symbol": "BTC/USDT",
  "exchange": "okx",
  "timeframe": "1m"
}
```

### State File
```json
{
  "last_timestamp_utc": "2023-12-14T15:30:45.123Z",
  "last_trade_id": "123456",
  "last_cvd": "1234567.89"
}
```

---

## USAGE

### Process Single Symbol
```bash
python run_cvd_from_jsonl.py --symbol BTC-USDT
```

### Process Both Symbols
```bash
run_cvd.bat
```

---

## STATE MANAGEMENT

**State File:** `Vault\state\cvd\okx\{SYMBOL}.state.json`

Tracks:
- `last_timestamp_utc` - Last processed trade timestamp
- `last_trade_id` - Last processed trade ID (for same-timestamp ordering)
- `last_cvd` - Current CVD value

**Cursor Logic:**
- Only processes trades AFTER (timestamp, trade_id) cursor
- Prevents reprocessing on reruns
- Handles same-millisecond trades via numeric trade_id sort

---

## DEDUPLICATION

**Problem:** Running twice on same day could duplicate 1m windows

**Solution:** 
1. Read existing output file for that date
2. Track existing window_start_utc values
3. Only append new windows
4. Idempotent: re-running same minute = no duplicates

---

## CALCULATION DETAILS

### Size USD
```
size_usd = Decimal(price) * Decimal(size)
```

### CVD Update
```python
if trade.side == 'buy':
    cvd += size_usd
elif trade.side == 'sell':
    cvd -= size_usd
```

### Window Assignment
```python
window_start = floor_to_minute(trade.timestamp)
windows[window_start] = cvd  # Always latest CVD for that minute
```

---

## DEPENDENCIES

- Python 3.7+
- No external packages (stdlib only)
- Decimal for precision (no float errors)

---

## MONITORING

Check state file to see progress:
```bash
type "C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault\state\cvd\okx\BTC-USDT.state.json"
```

Check output windows:
```bash
type "C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault\derived\cvd\okx\BTC-USDT\1m\2023-12-14.jsonl"
```

---

## INTEGRATION WITH OKX HUB

OKX Hub writes trades → CVD reads trades

**Flow:**
1. OKX Hub streams live trades
2. Writes to `Vault\raw\okx\trades\{SYMBOL}\{DATE}.jsonl`
3. Run CVD calculator (manually or on schedule)
4. CVD reads new trades, updates state, writes 1m windows

**Frequency:**
- OKX Hub: Continuous streaming
- CVD Calc: Run every 1-5 minutes (or after hub writes batch)

---

## FUTURE: HTF ROLLUP

Separate script to derive HTF from 1m:

```python
# Pseudo-code for 1h rollup
for hour in date_range:
    # Get 1m CVD at minute :59
    cvd_1h = get_cvd_at(hour, minute=59)
    write_1h_window(hour, cvd_1h)
```

This keeps 1m as single source of truth.

---

**1m ground truth. HTF derived. No SQL. Pure JSONL.**
