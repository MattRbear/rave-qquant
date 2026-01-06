# RAVE_QUANT_VAULT

**Centralized data storage for all RaveQuant trading bots**

---

## PURPOSE

Single source of truth for all market intelligence streams. Every bot writes to isolated inbox folders here → clean separation, unified backup, cross-bot correlation enabled.

---

## ARCHITECTURE

```
Rave_Quant_Vault/
└── inbox/
    ├── coinalyze_oi/        ← Coinalyze: Open Interest
    ├── coinalyze_liqs/      ← Coinalyze: Liquidations
    ├── coinalyze_funding/   ← Coinalyze: Funding Rates
    ├── coinalyze_bullbear/  ← Coinalyze: Long/Short Ratio
    ├── okx_trades/          ← OKX: Trade data (future)
    ├── whale_alert/         ← Whale Alert: Large txns (future)
    └── [other bots...]
```

---

## INBOX PATTERN

Each bot owns its inbox namespace:
- **Append-only** - Never overwrites, always adds
- **Timestamped** - `{SYMBOL}_{TYPE}_{TIMESTAMP}.jsonl`
- **JSON Lines** - One record per line, streamable
- **Isolated** - Bot failures don't corrupt other streams

---

## DATA RETENTION

**Policy:** Manual cleanup (no auto-delete)  
**Compression:** Optional (gzip old .jsonl files)  
**Archival:** Move to separate archive/ folder when >30 days old

---

## CURRENT ACTIVE STREAMS

### Coinalyze Bot
- **Location:** `inbox/coinalyze_*`
- **Symbols:** BTC, ETH
- **Interval:** 1min
- **Streams:**
  - Open Interest
  - Liquidations
  - Funding Rates
  - Bull/Bear Ratio

---

## ACCESSING DATA

### Python Example
```python
from pathlib import Path
import json

vault = Path(r'C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault')

# Get latest OI file for BTC
oi_path = vault / 'inbox' / 'coinalyze_oi'
latest_file = sorted(oi_path.glob('BTC_oi_*.jsonl'))[-1]

# Read records
with open(latest_file, 'r') as f:
    for line in f:
        record = json.loads(line)
        print(record)
```

### Cross-Stream Correlation
```python
# Load multiple streams at once
streams = {
    'oi': vault / 'inbox' / 'coinalyze_oi',
    'liqs': vault / 'inbox' / 'coinalyze_liqs',
    'funding': vault / 'inbox' / 'coinalyze_funding'
}

# Sync timestamps across streams
for stream_name, stream_path in streams.items():
    latest = sorted(stream_path.glob('BTC_*.jsonl'))[-1]
    # Process...
```

---

## MONITORING

**Disk usage:**
```bash
cd "C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault"
dir /s
```

**Stream health:**
```python
# Check last write time per stream
for stream in vault.glob('inbox/*'):
    latest = sorted(stream.glob('*.jsonl'))[-1]
    age = datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)
    print(f"{stream.name}: Last write {age} ago")
```

---

## BACKUP STRATEGY

1. **Daily:** Copy entire vault to external drive
2. **Weekly:** Compress old files (>7 days)
3. **Monthly:** Archive to cloud storage

---

## FILE NAMING CONVENTION

**Format:** `{SYMBOL}_{TYPE}_{TIMESTAMP}.jsonl`

**Examples:**
- `BTC_oi_20231214_153045.jsonl`
- `ETH_liqs_20231214_153047.jsonl`
- `BTC_funding_20231214_153050.jsonl`

**Timestamp:** `YYYYMMDD_HHMMSS` (sortable)

---

## EXPANSION PLAN

### Upcoming Streams
- [ ] OKX trades (`okx_trades/`)
- [ ] Whale Alert large transactions (`whale_alert/`)
- [ ] Nansen smart money flows (`nansen_flows/`)
- [ ] USDT dominance (`usdt_dominance/`)

---

**Unified vault. Isolated streams. Scalable architecture.**
