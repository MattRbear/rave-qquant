# Volume Analyzer - Research Implementation Audit

## ✅ RESEARCH COMPLIANCE COMPLETE

This implementation **fully complies** with Section 6 (Anomaly Detection) of the quantitative research audit.

---

## CHANGES MADE (2025-12-15)

### **BEFORE:**
- ✅ Median-based tier classification (correct)
- ✅ Absorption detection (correct)
- ✅ Divergence detection (correct)
- ❌ No MAD-based anomaly detection
- ❌ No Modified Z-Score
- ❌ No robust outlier handling

### **AFTER:**
- ✅ **MAD Calculation** - Median Absolute Deviation for robustness
- ✅ **Modified Z-Score** - Outlier-resistant anomaly detection
- ✅ **Volume Anomaly Flagging** - |Mi| > 3.5 threshold
- ✅ **All existing features** - Maintained and working

---

## RESEARCH-VERIFIED FORMULAS

### 1. Median Absolute Deviation (MAD)

**Research Formula (Section 6.1):**
```
1. Calculate median: X̃ = median(X)
2. Calculate absolute deviations: |Xi - X̃|
3. Calculate MAD: MAD = median(|Xi - X̃|)
```

**Why MAD (Not Standard Deviation):**
```
Problem with σ (Standard Deviation):
- Single flash crash can blow out σ
- Squashes Z-scores of subsequent anomalies (Masking)
- Mean dragged by outliers (Swamping)

MAD Advantages:
- Uses median (robust to outliers)
- Not corrupted by extreme events
- Reliable in heavy-tailed distributions
```

**Status:** ✅ IMPLEMENTED

**Research Quote:**
> "In crypto, a single massive volatility event (flash crash) can blow out the standard deviation (σ), effectively 'squashing' the Z-scores of all subsequent anomalies, making them undetectable (Masking effect). Conversely, the mean (μ) can be dragged by the outlier, making normal data points look anomalous (Swamping effect)."

---

### 2. Modified Z-Score

**Research Formula (Section 6.1):**
```
Mi = 0.6745 × (Xi - X̃) / MAD

Where:
- 0.6745 is scaling constant
- Makes MAD consistent with σ of normal distribution
- σ ≈ 1.4826 × MAD

Anomaly Threshold: |Mi| > 3.5
```

**Status:** ✅ IMPLEMENTED

**Research Quote:**
> "The constant 0.6745 scales the MAD to be consistent with the standard deviation of a normal distribution (since σ ≈ 1.4826 × MAD). Anomaly threshold is typically |Mi| > 3.5. This method reliably detects volume spikes and price anomalies without being corrupted by the outliers themselves."

**Why 0.6745 Constant:**
```
For a normal distribution:
  σ = 1.4826 × MAD
  1 / 1.4826 = 0.6745

This scaling makes Modified Z-Score comparable to traditional Z-Score
when data is normal, but remains robust when data is heavy-tailed.
```

---

### 3. Anomaly Detection Logic

**Implementation:**
```python
def detect_volume_anomaly(volume, volume_history, threshold=3.5):
    1. Convert history to Decimal
    2. Calculate Modified Z-Score
    3. Check if |Modified Z| > threshold
    4. Return (is_anomaly, z_score)
```

**Use Cases:**
- **Volume Spike Detection**: Whale entry/exit
- **Manipulation Detection**: Pump & dump signatures
- **Event Detection**: News-driven volume surges
- **False Breakout Filtering**: Volume confirmation

**Example:**
```
Normal volume range: 5M - 15M
Sudden 50M volume bar:

Traditional Z-Score (corrupted by outliers):
  Z = (50M - 20M) / 15M = 2.0  ← NOT FLAGGED (false negative)

Modified Z-Score (robust):
  Mi = 0.6745 × (50M - 12M) / 3M = 8.5  ← FLAGGED (correct)
```

---

## OUTPUT FORMAT

**File:** `Vault/derived/volume/okx/perps/{INSTID}/volume_1m.jsonl`

**New Fields:**
```json
{
  "timestamp_utc": "2025-12-15T14:35:00Z",
  "instId": "BTC-USDT-SWAP",
  "total_volume": "25432100.50",
  "volume_tier": "T3",
  "volume_anomaly": true,
  "modified_z_score": "4.23",
  "absorption": false,
  "divergence": false,
  ...
}
```

**Key Additions:**
- `volume_anomaly` - Boolean flag (|Mi| > 3.5)
- `modified_z_score` - Raw score for magnitude assessment

---

## INTERPRETING MAD ANOMALIES

### Anomaly Magnitude Bands

**Modified Z-Score Interpretation:**
```
|Mi| < 3.5:  Normal (not anomalous)
|Mi| = 3.5-5.0:  Moderate anomaly (watch closely)
|Mi| = 5.0-7.0:  Strong anomaly (high confidence)
|Mi| > 7.0:  Extreme anomaly (whale/manipulation)
```

---

### Confluence Strategies

**Anomaly + Absorption (BULLISH)**
```
Setup:
✓ Volume anomaly (Mi > 3.5)
✓ Absorption (price flat despite volume)
✓ CVD falling (aggressive selling)
✓ Price holds support

Interpretation:
  Whale is absorbing massive selling pressure via limit buy wall
  → ACCUMULATION → Long setup
```

**Anomaly + Divergence (REVERSAL)**
```
Setup:
✓ Volume anomaly (Mi > 3.5)
✓ Price HH
✓ CVD LH (less aggressive buying)

Interpretation:
  Volume spike but decreasing buyer aggression
  → EXHAUSTION → Short setup
```

**Anomaly + Wick (BREAKOUT CONFIRMATION)**
```
Setup:
✓ Volume anomaly on breakout bar
✓ Wick retest with positive delta
✓ OBI > +0.6 (bid support)

Interpretation:
  High-conviction breakout with flow confirmation
  → CONTINUATION → Long setup
```

---

## CRITICAL DIFFERENCES: MAD vs STDDEV

### Example: Flash Crash Impact

**Dataset:** 20 bars of volume: [10M, 12M, 11M, 13M, 9M, ... , 200M (flash crash), 11M, 10M]

**Traditional Method (BROKEN):**
```
Mean = 20M (dragged up by flash crash)
StdDev = 40M (blown out by flash crash)

New 15M bar:
  Z = (15M - 20M) / 40M = -0.125  ← NOT FLAGGED (should be normal)

New 30M bar:
  Z = (30M - 20M) / 40M = 0.25    ← NOT FLAGGED (should be anomaly!)
```

**MAD Method (ROBUST):**
```
Median = 11M (not affected by flash crash)
MAD = 1.5M (not blown out)

New 15M bar:
  Mi = 0.6745 × (15M - 11M) / 1.5M = 1.8  ← Correctly normal

New 30M bar:
  Mi = 0.6745 × (30M - 11M) / 1.5M = 8.5  ← Correctly flagged!
```

**Key Insight:**
MAD ignores the flash crash outlier completely, maintaining detection sensitivity.

---

## VOLUME TIER SYSTEM (Existing)

**Tier Classification:**
```
T1: < 0.5x median   (Low - potential trap/manipulation)
T2: 0.5x - 1.0x     (Normal)
T3: 1.0x - 2.0x     (High - conviction move)
T4: > 2.0x median   (Extreme - WHALE TERRITORY)
```

**Tier + Anomaly Confluence:**
```
T4 + Anomaly = Likely institutional flow
T1 + No Anomaly = Quiet consolidation
T4 + No Anomaly = Gradual institutional accumulation (spread over time)
T2 + Anomaly = Sudden event (news, manipulation)
```

---

## ABSORPTION DETECTION (Existing)

**Logic:**
```
Price change < 0.5%  (flat)
Volume > 2x median   (surging)
→ Whale absorbing aggression
```

**Research Connection:**
Absorption often triggers anomaly AND shows flat price → double confirmation

---

## DIVERGENCE DETECTION (Existing)

**Logic:**
```
Price direction ≠ Delta direction

Price up + Delta down = Exhaustion (SHORT)
Price down + Delta up = Absorption (LONG)
```

**Research Connection:**
Divergence + Anomaly = High-conviction reversal signal

---

## RESEARCH AUDIT SCORE

| Requirement | Status |
|-------------|--------|
| MAD Calculation | ✅ CORRECT |
| Modified Z-Score | ✅ CORRECT |
| 0.6745 Scaling Constant | ✅ CORRECT |
| Anomaly Threshold (3.5) | ✅ CORRECT |
| Robust to Outliers | ✅ VERIFIED |
| Volume Tier Classification | ✅ CORRECT |
| Absorption Detection | ✅ CORRECT |
| Divergence Detection | ✅ CORRECT |

**Overall: 8/8 - FULL COMPLIANCE** ✅

---

## CRITICAL RESEARCH NOTES

### ✅ WHAT WE DO (Per Research)

1. **Median-Based Robustness**
   - Median not affected by outliers
   - MAD calculated from median (not mean)
   - Modified Z-Score uses median center

2. **Proper Scaling**
   - 0.6745 constant for normal distribution consistency
   - Threshold of 3.5 (equivalent to ~3σ in normal dist)

3. **Multi-Modal Detection**
   - Volume anomaly (statistical)
   - Absorption (structural)
   - Divergence (flow-based)

### ❌ COMMON MISTAKES (Research Warns)

1. **Using Standard Deviation**
   ```
   σ corrupted by outliers in crypto ❌
   MAD robust to heavy tails ✅
   ```

2. **Using Mean**
   ```
   Mean dragged by extremes ❌
   Median ignores extremes ✅
   ```

3. **Fixed Thresholds**
   ```
   "Volume > 50M" breaks across assets ❌
   "Mi > 3.5" works universally ✅
   ```

---

## LEPTOKURTIC DISTRIBUTIONS

**Research Context:**
> "Crypto markets are 'leptokurtic' (heavy-tailed). Extreme events occur far more frequently than a Normal (Gaussian) distribution predicts."

**What This Means:**
```
Normal Distribution:
  99.7% of data within ±3σ
  Extreme events rare

Crypto Distribution:
  Fat tails (more extremes)
  Flash crashes common
  Standard tools fail
```

**MAD Solution:**
Uses percentile-based approach (median) rather than moment-based (mean/variance), making it distribution-agnostic.

---

## NEXT STEPS

1. ✅ Volume Analyzer fully compliant with research
2. ✅ All core systems (VWAP, CVD, Buckets, Volume) verified
3. 🔄 Next: Final system-wide verification
4. 📋 Generate master compliance report

---

## INTEGRATION NOTES

**This anomaly detector feeds into:**
1. **Signal Dashboard** - Real-time anomaly alerts
2. **Confluence Analyzer** - Multi-metric confirmation
3. **Risk Engine** - Position sizing adjustments
4. **Alert System** - Whale movement notifications

**Recommended Thresholds by Use Case:**
- **Conservative Trading**: Mi > 4.0 (fewer false positives)
- **Standard Trading**: Mi > 3.5 (research default)
- **Aggressive/HFT**: Mi > 3.0 (higher sensitivity)
