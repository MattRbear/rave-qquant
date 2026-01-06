# COINALYZE BOT - ADVERSARIAL MARKET INTELLIGENCE

**Liquidity tracker. Hunt mode enabled.**

---

## MISSION

Track market maker behavior through:
- **Open Interest** - Where leverage is concentrated
- **Liquidations** - Where retail got hunted
- **Funding Rate** - Cost of holding positions
- **Bull/Bear Ratio** - Sentiment divergence from price

**Target:** BTC + ETH only  
**Interval:** 1min (captures volatility spikes)  
**Storage:** Append-only vault/inbox architecture

---

## TRACKED METRICS

### Open Interest (OI)
- **What:** Total $ value of open positions
- **Why:** Rising OI + flat price = compression (explosion incoming)
- **Hunt:** OI spike without price move = stops being layered

### Liquidations
- **What:** Forced position closures
- **Why:** Liquidation clusters = market maker sweeps
- **Hunt:** Liq spike → reversal zone (retail exit = smart entry)

### Funding Rate
- **What:** Cost to hold long vs short
- **Why:** Extreme funding = overcrowded trade
- **Hunt:** Funding flip = sentiment shift before price

### Bull/Bear Ratio (Long/Short Ratio)
- **What:** Ratio of long vs short positions
- **Why:** Extreme ratios = contrarian signal
- **Hunt:** 80%+ longs = fuel for liquidation cascade

---

## ARCHITECTURE

```
Coinalyze API
     ↓
 [1min polling]
     ↓
C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault\inbox\
  ├─ coinalyze_oi/        ← Open Interest
  ├─ coinalyze_liqs/      ← Liquidations
  ├─ coinalyze_funding/   ← Funding Rate
  └─ coinalyze_bullbear/  ← Long/Short Ratio
```

**Storage Format:** JSON Lines (.jsonl)  
Each line = one data point with timestamp

---

## INSTALLATION

```bash
cd "C:\Users\M.R Bear\Documents\RaveQuant\coinayalze_bot"
pip install -r requirements.txt
```

---

## USAGE

### Single Fetch (60min history)
```bash
python coinalyze_bot.py --once
```

### Continuous Mode (1min interval)
```bash
python coinalyze_bot.py
```

Fetches last 5 minutes every 60 seconds to avoid duplicates.

---

## CONFIGURATION

**API Key:** Set `COINALYZE_API_KEY` in environment or `all env.txt`

**Symbols:** BTC, ETH (BTCUSDT_PERP.A, ETHUSDT_PERP.A)

**Intervals:**
- OI: 1min
- Liquidations: 1min
- Funding: 1min
- Bull/Bear: 1min

**Rate Limit:** 40 calls/minute (enforced automatically)

---

## DATA STRUCTURE

### Example Open Interest Record
```json
{
  "t": 1640000000,
  "o": 12500000000
}
```
- `t` = timestamp (unix)
- `o` = open interest value (USD)

### Example Liquidation Record
```json
{
  "t": 1640000000,
  "lq": 5000000,
  "s": "long"
}
```
- `t` = timestamp
- `lq` = liquidation volume (USD)
- `s` = side (long/short)

### Example Funding Rate Record
```json
{
  "t": 1640000000,
  "fr": 0.0001
}
```
- `t` = timestamp
- `fr` = funding rate (positive = longs pay shorts)

### Example Bull/Bear Record
```json
{
  "t": 1640000000,
  "ls": 1.25
}
```
- `t` = timestamp
- `ls` = long/short ratio (>1 = more longs)

---

## HEALTH MONITORING

Bot tracks:
- Total requests
- Successful/failed requests
- Rate limit hits
- Last fetch time

View stats after each fetch cycle or with `Ctrl+C`.

---

## RATE LIMITING

**Coinalyze Limit:** 40 calls/minute

**Bot Strategy:**
1. Tracks request timestamps
2. Enforces 60-second window
3. Auto-sleeps if limit approached
4. Adds 0.1s buffer for safety

**Calls per fetch:**
- 4 endpoints × 2 symbols = 8 calls/minute
- Well under 40/min limit

---

## ADVERSARIAL USE CASES

### 1. Liquidation Cascade Detector
Monitor liq spikes → identify sweep zones → wait for reversal confirmation

### 2. OI Divergence Scanner
Track OI vs price → rising OI + flat price = compression → position for breakout

### 3. Funding Flip Alert
Monitor funding sign changes → early signal of sentiment shift

### 4. Retail Trap Identifier
Bull/bear >80% + negative funding → overcrowded long → liquidation fuel

---

## FILE OUTPUTS

```
C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault\inbox\
├─ coinalyze_oi\
│  ├─ BTC_oi_20231214_153045.jsonl
│  └─ ETH_oi_20231214_153045.jsonl
├─ coinalyze_liqs\
│  ├─ BTC_liqs_20231214_153045.jsonl
│  └─ ETH_liqs_20231214_153045.jsonl
├─ coinalyze_funding\
│  ├─ BTC_funding_20231214_153045.jsonl
│  └─ ETH_funding_20231214_153045.jsonl
└─ coinalyze_bullbear\
   ├─ BTC_bullbear_20231214_153045.jsonl
   └─ ETH_bullbear_20231214_153045.jsonl
```

**Naming:** `{SYMBOL}_{TYPE}_{TIMESTAMP}.jsonl`  
**Format:** JSON Lines (one object per line, easy to stream/parse)

---

## LOGS

All activity logged to:
- **Console** - Real-time monitoring
- **coinalyze_bot.log** - Persistent file

---

## TROUBLESHOOTING

**"API key not found"**
- Set `COINALYZE_API_KEY` environment variable
- Or add to `all env.txt` in OneDrive/Desktop

**"Rate limit hit"**
- Bot auto-handles this with sleep
- Check `Retry-After` header in logs

**"No data returned"**
- Verify symbol format (BTCUSDT_PERP.A)
- Check Coinalyze API status
- Review logs for specific errors

---

## INTEGRATION

**With other bots:**
```python
from coinalyze_bot import CoinalyzeBot

bot = CoinalyzeBot(api_key="your-key")
oi_data = bot.fetch_open_interest('BTC', lookback_minutes=10)
```

**Vault consumption:**
```python
import json
from pathlib import Path

# Read latest OI file
vault_path = Path(r'C:\Users\M.R Bear\Documents\RaveQuant\Rave_Quant_Vault')
oi_path = vault_path / 'inbox' / 'coinalyze_oi'
latest = sorted(oi_path.glob('BTC_oi_*.jsonl'))[-1]

with open(latest, 'r') as f:
    for line in f:
        record = json.loads(line)
        print(record)
```

---

**Built for asymmetric warfare. Tracks the hunters.**
