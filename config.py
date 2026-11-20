"""
Settings for each FOMC meeting you track.

To add a meeting:
  1. Kalshi event ticker: KXFED-<YY><MON>, e.g. KXFED-26SEP for September 2026.
  2. Polymarket slug: run  py find_polymarket.py "fed decision september"
     and copy the slug it prints.
  3. decision_date: the SECOND day of the FOMC meeting (statement day).
     Dates: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
"""

MEETINGS = {
    "2026-10": {
        "decision_date": "2026-10-28",
        "kalshi_event": "KXFED-26OCT",
        "polymarket_slug": "fed-decision-in-october-20260617190323537",
    },
    "2026-12": {
        "decision_date": "2026-12-09",
        "kalshi_event": "KXFED-26DEC",
        "polymarket_slug": "fed-decision-in-december-20260729232808632",
    },
}

# Backup if FRED can't be reached: the CURRENT upper bound of the Fed's target
# range, in %. Check it at https://fred.stlouisfed.org/series/DFEDTARU and
# UPDATE THIS AFTER EVERY FED MEETING that changes rates.
FALLBACK_UPPER_BOUND = 4.00

# If FRED keeps timing out on your network, set this to False to skip it and
# go straight to FALLBACK_UPPER_BOUND (saves waiting for the timeouts).
USE_FRED = False

# The five outcomes every source gets converted into, smallest to largest.
OUTCOMES = ["cut_50+", "cut_25", "hold", "hike_25", "hike_50+"]

# The Fed moves in steps of 0.25 percentage points (25 basis points).
STEP = 0.25
