# ANALYSIS TOOLS - Post-Processing & Signal Detection

**Similar to zone_analyzer.py and events_analyzer.py from wick collector, but for your RaveQuant system.**

---

## TOOLS

### **1. Confluence Analyzer**
Multi-layer signal detection - finds max conviction setups.

**What it does:**
- Reads all data sources (wicks, volume, buckets, CVD, VWAP)
- Identifies price levels where multiple signals align
- Scores confluence strength (0-100)
- Ranks trade setups by conviction

**Confluence layers:**
- Untouched wick (base: 20 points)
- Volume tier T4 (+15)
- Absorption (+15)
- Bucket wall >1M (+15)
- Bucket imbalance >0.7 (+10)
- Young wall <5min (+10)
- CVD aligned (+10)
- VWAP confluence (+5)

**Usage:**
```bash
cd Analysis
python confluence_analyzer.py --instId BTC-USDT-SWAP

# Or batch
run_confluence.bat
```

**Output:**
```
MAX CONVICTION SIGNALS (3 found)
================================================================================

#1 | Score: 85/100 | SHORT @ 101250.0
    Wick: high on 1h (age: 35min)
    Signals: WICK, VOL_T4, ABSORPTION, WALL_2.5M, IMB_0.82, YOUNG_120s, CVD_ALIGNED
    Layers: 7

#2 | Score: 70/100 | LONG @ 100950.0
    Wick: low on 15m (age: 18min)
    Signals: WICK, VOL_T4, WALL_1.8M, IMB_0.75, CVD_ALIGNED
    Layers: 5
```

**File output:**
```
C:\Users\M.R Bear\Documents\RaveQuant\Analysis\confluence_signals.jsonl
```

---

### **2. Signal Dashboard**
Real-time system health check.

**What it does:**
- Shows current state of all metrics
- Checks data freshness (< 15 min = fresh)
- Displays untouched wick count
- Shows volume tier + absorption
- Shows liquidity bucket walls
- Shows CVD direction
- Shows VWAP levels

**Usage:**
```bash
cd Analysis
python signal_dashboard.py --instId BTC-USDT-SWAP

# Or batch
run_dashboard.bat
```

**Output:**
```
================================================================================
 SIGNAL DASHBOARD - BTC-USDT-SWAP
================================================================================
 Generated: 2025-12-14 23:45:00 UTC
================================================================================

✅ UNTOUCHED WICKS: FRESH
   Total: 12 | Recent (1h): 3
   Age: 2 minutes

✅ VOLUME: FRESH
   Tier: 🔴 T4
   Absorption: 🚨 YES
   Divergence: No
   Age: 1 minutes

✅ LIQUIDITY BUCKETS: FRESH
   Young Bid Walls: 2
   Young Ask Walls: 3
   Age: 2 minutes

✅ CVD: FRESH
   Direction: 🐻 BEARISH
   Delta: -125000
   Age: 1 minutes

✅ VWAP: FRESH
   1H: 101240.5
   Session: 101210.0
   Age: 1 minutes

================================================================================
 SYSTEM HEALTH
================================================================================
✅ ALL SYSTEMS OPERATIONAL

================================================================================
```

---

## MASTER RUNNER

**Located:** `C:\Users\M.R Bear\Documents\RaveQuant\run_all.py`

**What it does:**
1. Checks Python version (3.8+)
2. Checks all components exist
3. Installs requirements
4. Starts data collectors (trades, L2, Coinalyze)
5. Runs all calculators (CVD, VWAP, wicks, volume, buckets)
6. Provides status

**Usage:**
```bash
cd C:\Users\M.R Bear\Documents\RaveQuant

# Full startup
python run_all.py

# Or batch
run_all.bat

# Check only (no start)
python run_all.py --check-only

# Skip collectors (data already flowing)
python run_all.py --no-start

# Specify instruments
python run_all.py --instIds BTC-USDT-SWAP ETH-USDT-SWAP
```

**Flow:**
```
1. Check Python ✓
2. Check components ✓
3. Install requirements (if needed)
4. Start trades collector
5. Start L2 collector
6. Start Coinalyze
7. Wait 30s for data
8. Run CVD calculator (BTC, ETH)
9. Run VWAP calculator (BTC, ETH)
10. Run wick detector (BTC, ETH)
11. Run volume analyzer (BTC, ETH)
12. Run bucket calculator (BTC, ETH)
13. Done → System operational
```

---

## COMPARISON TO UPLOADED SCRIPTS

### **zone_analyzer.py → confluence_analyzer.py**

**Similar:**
- Post-processing of collected data
- Clustering/aggregation logic
- Scoring system
- Best setup identification
- Lifecycle tracking

**Your version adds:**
- Multi-source confluence (not just wicks)
- Volume signals (absorption/divergence)
- Liquidity bucket integration
- CVD alignment
- VWAP confluence

### **events_analyzer.py → signal_dashboard.py**

**Similar:**
- Summary statistics
- Grouped analysis
- Data freshness checks
- Playbook generation (hold windows)

**Your version adds:**
- Real-time system health
- Component status monitoring
- Multi-metric dashboard
- Visual status (emojis, formatting)

---

## WORKFLOW

### **Daily Trading Routine:**

**1. Startup (once per day):**
```bash
cd RaveQuant
run_all.bat
```

**2. Check system health (every 30-60 min):**
```bash
cd Analysis
run_dashboard.bat
```

**3. Find trade setups (when looking for entry):**
```bash
cd Analysis
run_confluence.bat
```

**4. Execute trade when:**
- Confluence score >= 70
- System health = ALL OPERATIONAL
- Multiple layers aligned (5+)
- Wick age 20-40 min (your sweet spot)
- Volume tier T3 or T4
- Young wall present

---

## FILES

```
Analysis\
├── confluence_analyzer.py       - Multi-layer signal detection
├── signal_dashboard.py          - System health dashboard
├── run_confluence.bat           - Confluence runner
├── run_dashboard.bat            - Dashboard runner
├── confluence_signals.jsonl     - Output (generated)
└── README.md                    - This file

RaveQuant\
├── run_all.py                   - Master runner
└── run_all.bat                  - Master batch
```

---

## TIPS

**When confluence analyzer returns empty:**
- Check dashboard (system operational?)
- Check wick age (all >60min stale?)
- Check volume tier (all T1 noise?)
- Lower score threshold in code (line 243: `>= 50` → `>= 40`)

**When dashboard shows STALE:**
- Check if collectors running
- Check if calculators ran recently
- Re-run master runner

**When data missing:**
- Check vault paths in each script
- Verify data files exist
- Check file permissions

---

**Analysis tools complete. Similar to your uploaded scripts, but fitted to RaveQuant system.**
