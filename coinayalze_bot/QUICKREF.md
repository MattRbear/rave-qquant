# COINALYZE BOT - QUICK REFERENCE

## 🎯 MISSION
Track BTC + ETH market maker behavior via Coinalyze API

---

## ⚡ QUICK START
```bash
cd "C:\Users\M.R Bear\Documents\RaveQuant\coinayalze_bot"
python coinalyze_bot.py
```

---

## 📊 DATA TRACKED

| Metric | Endpoint | Interval | Why Track |
|--------|----------|----------|-----------|
| Open Interest | `/open-interest-history` | 1min | Leverage concentration |
| Liquidations | `/liquidation-history` | 1min | Retail hunt zones |
| Funding Rate | `/funding-rate-history` | 1min | Position cost shifts |
| Bull/Bear Ratio | `/long-short-ratio-history` | 1min | Sentiment divergence |

---

## 📁 STORAGE LOCATIONS
```
C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault\inbox\
  ├─ coinalyze_oi\        ← Open Interest
  ├─ coinalyze_liqs\      ← Liquidations  
  ├─ coinalyze_funding\   ← Funding Rate
  └─ coinalyze_bullbear\  ← Long/Short Ratio
```

**Format:** `{SYMBOL}_{TYPE}_{TIMESTAMP}.jsonl`

---

## 🔧 COMMANDS

### Run Continuous (1min interval)
```bash
python coinalyze_bot.py
```

### Single Fetch (60min history)
```bash
python coinalyze_bot.py --once
```

### Windows Launcher
```bash
start_bot.bat
```

---

## 🎮 CONFIGURATION

**API Key:** `COINALYZE_API_KEY=5a61e1ac-38a5-4305-a058-e8af0b581237`  
(Already in `all env.txt`)

**Symbols:** BTC (`BTCUSDT_PERP.A`), ETH (`ETHUSDT_PERP.A`)

**Rate Limit:** 40 calls/min (bot uses 8/min)

---

## 📊 DATA FORMAT

### Open Interest
```json
{"t": 1640000000, "o": 12500000000}
```

### Liquidations
```json
{"t": 1640000000, "lq": 5000000, "s": "long"}
```

### Funding Rate
```json
{"t": 1640000000, "fr": 0.0001}
```

### Bull/Bear Ratio
```json
{"t": 1640000000, "ls": 1.25}
```

---

## 🔍 ADVERSARIAL PATTERNS

### Liquidation Sweep
- **Signal:** Liq spike > 3× average
- **Action:** Wait for reversal confirmation

### OI Compression
- **Signal:** OI +20% + flat price
- **Action:** Position for breakout

### Funding Flip
- **Signal:** Funding crosses zero
- **Action:** Sentiment shift confirmation

### Retail Trap
- **Signal:** Bull/bear >80% + negative funding
- **Action:** Liquidation cascade fuel

---

## 🛡️ ERROR HANDLING

- Network failures → Auto-retry
- Rate limits → Auto-sleep
- API errors → Logged, continue
- Ctrl+C → Graceful shutdown

---

## 📁 FILES

| File | Purpose |
|------|---------|
| `coinalyze_bot.py` | Core engine (358 lines) |
| `README.md` | Full documentation |
| `DEPLOYMENT.md` | Ops guide |
| `start_bot.bat` | Launcher |
| `requirements.txt` | Dependencies |

---

## ⚙️ HEALTH CHECK
```python
from coinalyze_bot import CoinalyzeBot

bot = CoinalyzeBot(api_key="...")
stats = bot.get_stats()
print(stats)
```

---

**Fast reference. No fluff. Hunt mode.**
