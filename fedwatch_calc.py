"""
Your own version of CME FedWatch: turn a 30-day fed funds futures (ZQ) price
into probabilities for the next Fed decision.

Key fact: a ZQ contract settles at 100 minus the AVERAGE effective fed funds
rate (EFFR) over its month. So 100 - price = the rate the market expects,
averaged across the month.

Run this file to see a worked example:   py fedwatch_calc.py
"""

import calendar
import math

import pandas as pd

from config import OUTCOMES

BP_PER_STEP = 25   # the Fed moves in 25 basis-point steps


def expected_change_clean_month(next_month_price, effr_now):
    """
    Use when there is NO meeting in the contract's month, so the whole month
    reflects the post-decision rate. (October meeting -> use the NOVEMBER contract.)
    Returns the expected change in basis points (+ = hike, - = cut).
    """
    implied_rate = 100 - next_month_price
    return (implied_rate - effr_now) * 100


def expected_change_meeting_month(price, effr_now, decision_day, year, month):
    """
    Use the contract for the meeting's own month. The new rate starts the day
    AFTER the decision, so the month is a mix of old and new rates:
        average = old * (days before) / D  +  new * (days after) / D
    Solve that for the new rate.
    (December 9 meeting -> 9 days at the old rate, 22 days at the new rate.)
    """
    days = calendar.monthrange(year, month)[1]
    days_old = decision_day
    days_new = days - decision_day
    average = 100 - price
    new_rate = (average - effr_now * days_old / days) / (days_new / days)
    return (new_rate - effr_now) * 100


def change_to_probabilities(expected_change_bp):
    """
    Spread an expected change across the two nearest 25 bp outcomes.
    Example: +7 bp expected -> 28% hike 25, 72% hold.
    """
    steps = expected_change_bp / BP_PER_STEP
    low = math.floor(steps)
    weight_high = steps - low
    names = {-2: "cut_50+", -1: "cut_25", 0: "hold", 1: "hike_25", 2: "hike_50+"}

    probs = {name: 0.0 for name in OUTCOMES}
    for step, weight in [(low, 1 - weight_high), (low + 1, weight_high)]:
        step = max(-2, min(2, step))        # anything bigger counts as 50+
        probs[names[step]] += weight
    return probs


def log_with_own_calc(path="data/fedwatch_log.csv"):
    """
    Read your daily hand log and add your own ZQ-based probabilities next to
    FedWatch's, so you can check how close you get.
    Uses the clean-month method (log the month AFTER the meeting).
    """
    log = pd.read_csv(path)
    own = log.apply(lambda r: change_to_probabilities(
        expected_change_clean_month(r["zq_price"], r["effr"])), axis=1)
    own = pd.DataFrame(list(own)).add_prefix("own_")
    return pd.concat([log, own], axis=1)


if __name__ == "__main__":
    # Illustrative numbers only, not real quotes.
    effr = 3.83
    nov_price = 96.10
    change = expected_change_clean_month(nov_price, effr)
    print(f"October meeting, clean-month method: expected change {change:+.1f} bp")
    for name, p in change_to_probabilities(change).items():
        print(f"  {name:9s} {p:6.1%}")

    # December: if the market fully expects a hike from 4.00 to 4.25 ...
    effr_dec, new_rate = 4.00, 4.25
    avg = effr_dec * 9 / 31 + new_rate * 22 / 31
    dec_price = 100 - avg
    change = expected_change_meeting_month(dec_price, effr_dec, 9, 2026, 12)
    print(f"\nDecember check: price {dec_price:.4f} -> expected change {change:+.1f} bp"
          " (should be +25.0)")
