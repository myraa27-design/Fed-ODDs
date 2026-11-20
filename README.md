# Fed Rate Expectations: Prediction Markets vs. the Rates Market

**Question:** Do prediction markets (Kalshi, Polymarket) and the fed funds futures
market agree on what the Fed will do, and when they disagree, which one is right first?

Tracking the **October 27–28** and **December 8–9, 2026** FOMC meetings live, plus
earlier 2026 meetings from price history.

> Status: 🟡 In progress. Data collection started Oct 2026.

## How each market expresses a probability

| Source | Contract | Conversion |
| --- | --- | --- |
| Kalshi (`KXFED`) | "Upper bound above X% after the meeting?" one contract per strike | Neighbouring strikes subtracted: P(= X + 0.25) = P(> X) − P(> X + 0.25) |
| Polymarket | One contract per outcome (cut 50+, cut 25, hold, hike 25, hike 50+) | Mid prices, normalised to sum to 1 |
| Fed funds futures (ZQ) / CME FedWatch | Settles at 100 − month's average EFFR | (implied rate − current EFFR) ÷ 25 bp |

All three are converted into the same five outcomes so they can be compared directly.

## Setup (Windows)

1. Install Python 3.12+ from [python.org](https://www.python.org/downloads/). Tick **"Add python.exe to PATH"** during install.
2. Open this folder in VS Code (or any terminal) and run:
   ```
   py -m pip install -r requirements.txt
   py check_math.py
   ```
   `check_math.py` should end with **All checks passed.**

## Daily routine (~5 minutes)

1. `py snapshot.py`: saves today's Kalshi and Polymarket probabilities to `data/snapshots.csv`.
2. Open [CME FedWatch](https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html) and add one line per meeting to `data/fedwatch_log.csv`. Use the **month after the meeting** for `zq_contract` (October meeting → November contract, ticker ZQX26). Probabilities are in %:
   ```
   date,meeting,zq_contract,zq_price,effr,fedwatch_cut_25,fedwatch_hold,fedwatch_hike_25,notes
   2026-10-16,2026-10,ZQX26,<price>,<EFFR from FRED>,<cut %>,<hold %>,<hike %>,<anything notable>
   ```

## Other scripts

| Command | What it does |
| --- | --- |
| `py history.py 2026-10` | Downloads daily history for a meeting from both venues → `data/history_2026-10.csv` + chart in `images/` |
| `py fedwatch_calc.py` | Worked example of turning a futures price into probabilities |
| `py find_polymarket.py "fed decision september"` | Finds the Polymarket slug for another meeting (add it to `config.py`) |

## Files

```
config.py          meetings tracked (Kalshi ticker, Polymarket slug, decision date)
sources.py         download + conversion functions for Kalshi, Polymarket, FRED
fedwatch_calc.py   futures price → probabilities (clean-month and meeting-month methods)
snapshot.py        daily logger
history.py         historical download + chart
check_math.py      offline checks of the maths
data/              snapshots.csv, fedwatch_log.csv, history_*.csv
images/            charts
```

## Data sources

- Kalshi public API: `api.elections.kalshi.com/trade-api/v2` (no key needed for market data)
- Polymarket Gamma API (`gamma-api.polymarket.com`) and CLOB price history (`clob.polymarket.com/prices-history`)
- FRED: DFEDTARU (target upper bound), EFFR (effective fed funds rate)
- CME FedWatch: logged by hand daily

## Caveats

- Kalshi settles on the **level** after a meeting; Polymarket on the **change** at that meeting. For a later meeting (December), compare the two only after the earlier meeting (October) has happened.
- Far-out Kalshi strikes are thinly traded, so mid prices are used and tiny probabilities are noise.
- Futures embed small EFFR drift and risk premia, so they aren't pure probabilities.
- Analysis only. No trading.

## Findings

_To be added after the October and December meetings._
