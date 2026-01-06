# CVD Calculator - Research Implementation Audit

## ✅ RESEARCH COMPLIANCE COMPLETE

This implementation **fully complies** with Section 3 (CVD) of the quantitative research audit.

---

## CHANGES MADE (2025-12-15)

### **BEFORE:**
- ✅ Correct CVD formula (was already correct)
- ❌ No delta per bar tracking
- ❌ No divergence pattern documentation

### **AFTER:**
- ✅ **Aggressor-based CVD** - Correct formula maintained
- ✅ **Delta Per Bar** - Added `cvd_delta` to output
- ✅ **Divergence Patterns** - Documented all research patterns
- ✅ **State Persistence** - Cumulative never-resetting CVD

---

## RESEARCH-VERIFIED FORMULAS

### 1. Delta Calculation (Per Trade)
```
Δt = V_ask,t - V_bid,t

Where:
  V_ask,t = volume from market BUY orders (aggressor pays ask)
  V_bid,t = volume from market SELL orders (aggressor hits bid)
```

**Aggressor Logic:**
- **Taker** = Aggressor (pays spread to initiate transaction)
- If `side = 'buy'` → Market buy hit limit sell → **+volume** (aggressive buying)
- If `side = 'sell'` → Market sell hit limit buy → **-volume** (aggressive selling)

**Status:** ✅ CORRECT

---

### 2. Cumulative Volume Delta
```
CVD_T = Σ(t=0 to T) Δt

CVD is cumulative and NEVER resets (maintains state across sessions)
```

**Interpretation:**
- **Rising CVD** → Aggressive buyers dominating flow
- **Falling CVD** → Aggressive sellers dominating flow

**Status:** ✅ CORRECT

**Research Quote:**
> "CVD transforms raw volume data into a directional vector of market aggression. It is not merely a volume indicator; it is a sentiment indicator derived from the mechanics of trade execution."

---

## CRITICAL DIVERGENCE PATTERNS (From Research)

### 1. Bullish Absorption (Limit Buy Wall)

**Setup:**
- Price: Makes Lower Low (LL) or trades flat at support
- CVD: Makes significantly Lower Low or trends down sharply

**Inference:**
```
Aggressive sellers are hammering the bid (negative Delta), 
but price is not breaking down further.

This implies a passive buyer is absorbing all sell liquidity 
via limit orders.

SIGNAL: Classic accumulation pattern (BULLISH)
```

**Example:**
```
Time    Price    CVD
10:00   $100k    +500k
10:05   $99.5k   +300k   ← Price LL
10:10   $99.5k   -200k   ← CVD MASSIVE LL (selling pressure)
10:15   $99.8k   -100k   ← Price holds, CVD recovers

Interpretation: Whale absorbed selling at $99.5k → LONG SETUP
```

---

### 2. Bearish Exhaustion (Buying into Resistance)

**Setup:**
- Price: Makes Higher High (HH)
- CVD: Makes Lower High (LH)

**Inference:**
```
Price is rising, but with LESS aggressive buying volume 
than the previous peak.

This indicates buyers are exhausted and the upward move 
is unsupported by flow.

SIGNAL: Often precedes a reversal (BEARISH)
```

**Example:**
```
Time    Price    CVD
10:00   $100k    +500k   ← HH in price
10:05   $100.2k  +800k   
10:10   $100.5k  +600k   ← CVD LH (less buying)
10:15   $100.3k  +550k   ← Reversal starts

Interpretation: Buyers exhausted → SHORT SETUP
```

---

### 3. Delta Turn Anomaly (HFT Signal)

**Setup:**
- Candle: Closes RED (price down)
- Delta: POSITIVE (net aggressive buying)

**Inference:**
```
Despite net aggressive buying (Positive Delta), 
price closed lower.

This indicates extremely heavy LIMIT SELLING (passive supply) 
that absorbed buy pressure and forced price down.

SIGNAL: Strong bearish continuation (BEARISH)
```

**Example:**
```
1-Minute Candle:
  Open: $100k
  Close: $99.8k  (RED candle)
  CVD Delta: +$2M (positive - aggressive buying!)

Interpretation: Whale sold passively into aggressive buyers
                → Price rejection → SHORT continuation
```

**Research Quote:**
> "A specific high-frequency signal often overlooked is the 'Delta Turn.' This occurs within a single bar timeframe. Despite net aggressive buying (Positive Delta), the price closed lower. This indicates extremely heavy limit selling that absorbed the buy pressure and forced price down."

---

## OUTPUT FORMAT

**File:** `Vault/derived/cvd/okx/{SYMBOL}/1m/{DATE}.jsonl`

**Structure:**
```json
{
  "window_start_utc": "2025-12-15T14:35:00Z",
  "cvd_value": "154327650.25",
  "cvd_delta": "-245320.15",
  "symbol": "BTC/USDT",
  "exchange": "okx",
  "timeframe": "1m"
}
```

**New Field:**
- `cvd_delta` - Delta for this specific 1m bar (buy_volume - sell_volume)
- Useful for identifying:
  - High aggression bars (|delta| > threshold)
  - Delta turns (price vs delta divergence)
  - Exhaustion (declining deltas in trend)

---

## USAGE EXAMPLES

### Standard CVD Calculation
```bash
python run_cvd_from_jsonl.py --symbol BTC-USDT
```

**Outputs:**
- Cumulative CVD (never resets)
- Per-bar Delta (resets each minute)

---

## INTERPRETING CVD IN CONFLUENCE

### With Price Action
```
Price + CVD Agreement:
  Price ↑ + CVD ↑ = Healthy uptrend (BULLISH)
  Price ↓ + CVD ↓ = Healthy downtrend (BEARISH)

Price vs CVD Divergence:
  Price ↑ + CVD ↓ = Exhaustion (BEARISH)
  Price ↓ + CVD ↑ = Absorption (BULLISH)
```

### With Volume Tiers
```
High Delta + T4 Volume = Strong aggression (confirm breakout)
Low Delta + T4 Volume = Absorption (accumulation/distribution)
```

### With VWAP
```
Price tests Session VWAP:
  Positive Delta = Buyers defending → LONG
  Negative Delta = Sellers rejecting → SHORT
```

---

## RESEARCH AUDIT SCORE

| Requirement | Status |
|-------------|--------|
| Aggressor-based Delta | ✅ CORRECT |
| Cumulative Summation | ✅ CORRECT |
| State Persistence | ✅ CORRECT |
| Delta Per Bar | ✅ ADDED |
| Divergence Documentation | ✅ ADDED |

**Overall: 5/5 - FULL COMPLIANCE** ✅

---

## CRITICAL RESEARCH NOTES

### ✅ WHAT WE DO (Per Research)

1. **Aggressor Tagging**
   - Side = 'buy' → Market buy → Aggressive buyer → +CVD
   - Side = 'sell' → Market sell → Aggressive seller → -CVD

2. **Cumulative Never-Resetting**
   - CVD maintains state across sessions
   - Reflects cumulative buying/selling pressure since inception

3. **Divergence Focus**
   - Research emphasizes: "The critical utility of CVD lies in its divergence from price action"
   - We now output both CVD and Delta for divergence analysis

### ❌ WHAT TO AVOID

1. **Volume as Proxy**
   - Simple volume doesn't show DIRECTION
   - CVD shows NET aggression (directional flow)

2. **Treating CVD as Oscillator**
   - CVD is NOT mean-reverting
   - It's a cumulative tape measure of pressure

3. **Ignoring Divergences**
   - Research: Divergences "reveal the presence of large passive traders (whales)"

---

## NEXT INTEGRATION

CVD Delta is now available for:
1. **Confluence Analyzer** - Combine with wicks, buckets, VWAP
2. **Volume Analyzer** - Enhance divergence detection
3. **Signal Dashboard** - Real-time delta turn detection

---

## NEXT STEPS

1. ✅ CVD fully compliant with research
2. 🔄 Next: Liquidity Buckets (OBI, Micro-price)
3. ⏳ Pending: MAD anomaly detection, OFI
