"""
Run this ONCE A DAY (same time each day is best):   py snapshot.py

It records today's probabilities from Kalshi and Polymarket for every upcoming
meeting in config.py, prints them, and adds them to data/snapshots.csv.

Then open the CME FedWatch tool and add today's numbers to data/fedwatch_log.csv
by hand (see README).

Note on Kalshi vs Polymarket for a LATER meeting (e.g. December, before the
October decision): Kalshi asks where the rate will be AFTER that meeting
(including any October move), while Polymarket asks about the change AT that
meeting only. So compare December directly only once October has happened.
"""

import os
from datetime import datetime, timezone

import pandas as pd

import sources
from config import FALLBACK_UPPER_BOUND, MEETINGS, OUTCOMES

OUT = "data/snapshots.csv"


def take_snapshot():
    now = datetime.now(timezone.utc)
    upper = sources.latest("DFEDTARU")     # upper bound of the Fed's target range
    if upper is None:
        upper = FALLBACK_UPPER_BOUND
        print(f"  Using FALLBACK_UPPER_BOUND = {upper:.2f}% from config.py")
    effr = sources.latest("EFFR")          # effective fed funds rate (1-day lag)
    effr_text = f"{effr:.2f}%" if effr is not None else "n/a"
    print(f"{now:%Y-%m-%d %H:%M} UTC | target upper bound {upper:.2f}% | EFFR {effr_text}")

    rows = []
    for meeting, info in MEETINGS.items():
        if pd.Timestamp(info["decision_date"]).date() < now.date():
            continue                       # meeting already happened

        for source in ["kalshi", "polymarket"]:
            try:
                if source == "kalshi":
                    probs = sources.kalshi_now(info["kalshi_event"], upper)
                else:
                    probs = sources.polymarket_now(info["polymarket_slug"])
            except Exception as error:     # keep going if one source is down
                print(f"  {meeting} {source}: failed ({error})")
                continue
            rows.append({"timestamp_utc": now.strftime("%Y-%m-%d %H:%M"),
                         "meeting": meeting, "source": source,
                         "upper_bound": upper, "effr": effr, **probs})

    if not rows:
        print("Nothing saved.")
        return None

    df = pd.DataFrame(rows)
    table = df.set_index(["meeting", "source"])[OUTCOMES]
    print()
    print((table * 100).round(1).to_string())      # shown in %

    os.makedirs("data", exist_ok=True)
    new_file = not os.path.exists(OUT)
    df.to_csv(OUT, mode="a", header=new_file, index=False)
    print(f"\nSaved {len(df)} rows to {OUT}")
    return df


if __name__ == "__main__":
    take_snapshot()
