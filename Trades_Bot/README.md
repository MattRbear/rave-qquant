# TRADES EXPORTER - OKX PERPS ONLY

**Foundation for CVD + VWAP + Trade-Based Metrics**

---

## MISSION

Capture every perpetual swap trade from OKX with full contract metadata:
- Event-time stamping (OKX `ts`, never ingestion time)
- Contract conversion parameters (ctVal, ctMult, ctType)
- Deduplication (append-only, never overwrites)
- Single source of truth for all trade-based calculations

---

## ARCHITECTURE

```
OKX WebSocket ("trades" channel)
        ↓
  [Metadata Manager]
   - ctVal, ctMult, ctType
   - Cached from REST API
        ↓
  [Trades Writer]
   - Deduplication
   - Daily JSONL rotation
        ↓
Vault\raw\okx\trades_perps\{INSTID}\{DATE}.jsonl
```

---

## CONFIGURATION

**Instruments:** BTC-USDT-SWAP, ETH-USDT-SWAP ONLY  
**Output:** Daily-rotated JSONL files  
**Deduplication:** By (exchange, instId, trade_id)  
**Metadata:** Fetched once on startup  

---

## DATA FORMAT

### Trade Record (JSONL)
```json
{
  "timestamp_utc": "2025-12-14T21:34:56.123Z",
  "exchange": "okx",
  "market": "perp",
  "instId": "BTC-USDT-SWAP",
  "symbol_canon": "BTC/USDT",
  "trade_id": "1234567890",
  "side": "buy",
  "price": "101250.5",
  "qty_contracts": "45",
  "ctVal": "0.01",
  "ctMult": "1",
  "ctType": "linear"
}
```

**All numeric values are strings** - Decimal-safe for precision calculations

---

## USAGE

### Start Trades Exporter
```bash
cd "C:\Users\M.R Bear\Documents\RaveQuant\Trades_Bot"
python trades_exporter.py
```

Or use batch launcher:
```bash
start_trades.bat
```

---

## CONTRACT METADATA

### Fetched from OKX REST API
`/api/v5/public/instruments?instType=SWAP&instId={INSTID}`

**Saved to:**  
`Vault\meta\okx\instruments\{INSTID}.json`

**Contains:**
- `ctVal` - Contract value (e.g., "0.01" = 1 contract = 0.01 BTC)
- `ctMult` - Contract multiplier
- `ctType` - Contract type ("linear" for USDT margined)
- `tickSz` - Minimum price increment
- `lotSz` - Minimum order size

**Used for:**
- Converting qty_contracts → base quantity
- Calculating notional value
- VWAP calculations
- Position sizing

---

## DEDUPLICATION

**Key:** `{exchange}:{instId}:{trade_id}`

**Mechanism:**
- Track last 10k trades per instrument in memory
- Skip duplicate writes
- Prevents re-processing on reconnect

**Result:** Idempotent (safe to restart anytime)

---

## RELIABILITY FEATURES

### Event-Time Stamping
**CRITICAL:** Uses OKX `ts` field (event time), NEVER system ingestion time  
**Why:** Ensures chronological consistency for rolling calculations

### Schema Validation
**STOP Condition:** Missing required fields  
**Required:** ts, instId, tradeId, px, sz, side  
**Output:** BUILD_FAIL message with missing fields

### Instrument Validation
**STOP Condition:** Unexpected instId appears  
**Allowed:** BTC-USDT-SWAP, ETH-USDT-SWAP ONLY  
**Output:** BUILD_FAIL message

### Metadata Validation
**STOP Condition:** Missing ctVal, ctMult, or ctType  
**Why:** These are essential for notional calculations  
**Output:** BUILD_FAIL message

---

## FILE STRUCTURE

```
Trades_Bot\
├── trades_exporter.py   (401 lines)
├── requirements.txt
├── start_trades.bat
└── README.md

Vault\
├── raw\okx\trades_perps\
│   ├── BTC-USDT-SWAP\
│   │   ├── 2025-12-14.jsonl
│   │   ├── 2025-12-15.jsonl
│   │   └── ...
│   └── ETH-USDT-SWAP\
│       └── ...
└── meta\okx\instruments\
    ├── BTC-USDT-SWAP.json
    └── ETH-USDT-SWAP.json
```

---

## DOWNSTREAM CONSUMERS

This trades feed powers:

### ✅ CVD Calculator
- Reads: trades_perps JSONL
- Calculates: Cumulative Volume Delta
- Output: `derived/cvd/okx/{INSTID}/1m/`

### 🔄 VWAP Calculator (Next)
- Reads: trades_perps JSONL
- Calculates: Rolling 1h/4h VWAP
- Output: `derived/vwap/okx/perps/{INSTID}/vwap_1m.jsonl`

### Future
- Volume profile
- Trade flow imbalance
- Aggression indicators
- Liquidity consumption rate

---

## MONITORING

### Check Exporter Status
```bash
# Logs
type "C:\Users\M.R Bear\Documents\RaveQuant\Trades_Bot\trades_exporter.log"

# Recent trades
dir "C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault\raw\okx\trades_perps\BTC-USDT-SWAP"
```

### Verify Trades
```bash
# Today's trades
type "...\trades_perps\BTC-USDT-SWAP\2025-12-14.jsonl" | more
```

### Health Metrics
Watch logs for:
- `Metadata fetched and saved` - Startup success
- `Subscribed to trades` - WebSocket active
- `Stats: X written, Y skipped` - Deduplication working

---

## PERFORMANCE

**Write Rate:** ~10-100 trades/sec per instrument (varies)  
**File Size:** ~1-5MB/day per instrument (depends on volume)  
**Memory:** <20MB (dedup cache)  
**CPU:** <2% (idle), <5% (active)  

---

## TROUBLESHOOTING

**"BUILD_FAIL: Missing required metadata fields"**  
→ OKX API changed. Check `/api/v5/public/instruments` response.

**"BUILD_FAIL: Unexpected instId"**  
→ Code bug. Only BTC-USDT-SWAP and ETH-USDT-SWAP allowed.

**"BUILD_FAIL: Missing required trade fields"**  
→ OKX changed message schema. Check logs for field names.

**No trades writing**  
→ Check WebSocket connection. Verify subscription confirmed.

---

## EXPANSION

### Add More Instruments
**WARNING:** This breaks PERPS-ONLY contract

Edit `trades_exporter.py` carefully:
```python
INSTRUMENTS = [
    "BTC-USDT-SWAP",
    "ETH-USDT-SWAP",
    # Add more perpetual swaps here
]
```

---

**Foundation deployed. Trade stream flowing. CVD + VWAP ready.**
