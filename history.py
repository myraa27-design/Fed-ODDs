"""
Download the daily price history for one meeting from Kalshi and Polymarket,
convert both into outcome probabilities, then save a CSV and a chart.

Usage:   py history.py 2026-10
Output:  data/history_2026-10.csv  and  images/history_2026-10.png
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import matplotlib.pyplot as plt
import pandas as pd

import sources
from config import FALLBACK_UPPER_BOUND, MEETINGS, OUTCOMES

DAYS_BACK = 120     # how far before the decision to start


def kalshi_history(event_ticker, upper_by_day, start_ts, end_ts):
    """One row per day: Kalshi outcome probabilities."""
    ladder = sources.kalshi_markets(event_ticker)
    columns = {}
    for _, market in ladder.iterrows():
        series = sources.kalshi_candles(market["ticker"], start_ts, end_ts)
        if len(series):
            columns[market["strike"]] = series
    prices = pd.DataFrame(columns).sort_index(axis=1).ffill().dropna()

    rows = []
    for day, row in prices.iterrows():
        upper = upper_by_day.asof(day)          # the Fed's range on that day
        probs = sources.ladder_to_outcomes(list(row.index), list(row.values), upper)
        rows.append({"date": day, **probs})
    return pd.DataFrame(rows).set_index("date")


def polymarket_history(slug):
    """One row per day: Polymarket outcome probabilities (normalised)."""
    markets = sources.polymarket_markets(slug)
    columns = {}
    for _, market in markets.iterrows():
        columns[market["outcome"]] = sources.polymarket_history(market["yes_token"])
    prices = pd.DataFrame(columns).ffill().dropna()
    for name in OUTCOMES:
        if name not in prices:
            prices[name] = 0.0
    prices = prices[OUTCOMES]
    return prices.div(prices.sum(axis=1), axis=0)


def fedwatch_points(meeting):
    """Your hand-logged FedWatch 'hold' probabilities for this meeting, if any."""
    path = "data/fedwatch_log.csv"
    if not os.path.exists(path):
        return pd.Series(dtype=float)
    log = pd.read_csv(path)
    log = log[log["meeting"] == meeting].dropna(subset=["fedwatch_hold"])
    if log.empty:
        return pd.Series(dtype=float)
    return pd.Series(log["fedwatch_hold"].values / 100,
                     index=pd.to_datetime(log["date"]))


def build(meeting):
    info = MEETINGS[meeting]
    decision = pd.Timestamp(info["decision_date"])
    now = datetime.now(timezone.utc)
    start = decision - timedelta(days=DAYS_BACK)
    end = min(now, (decision + timedelta(days=1)).tz_localize("UTC"))
    start_ts, end_ts = int(start.timestamp()), int(end.timestamp())

    try:
        fred = sources.fred_series("DFEDTARU").set_index("date")["value"].sort_index()
    except Exception:
        print(f"FRED unavailable, using {FALLBACK_UPPER_BOUND:.2f}% for every day")
        fred = pd.Series([FALLBACK_UPPER_BOUND], index=[start - timedelta(days=1)])

    print("Downloading Kalshi history ...")
    kalshi = kalshi_history(info["kalshi_event"], fred, start_ts, end_ts)
    print("Downloading Polymarket history ...")
    poly = polymarket_history(info["polymarket_slug"])
    poly = poly[(poly.index >= start) & (poly.index <= decision)]

    both = pd.concat({"kalshi": kalshi, "polymarket": poly}, names=["source", "date"])
    os.makedirs("data", exist_ok=True)
    csv_path = f"data/history_{meeting}.csv"
    both.to_csv(csv_path)
    print(f"Saved {csv_path}")

    chart(meeting, kalshi, poly, decision)
    return kalshi, poly


def chart(meeting, kalshi, poly, decision):
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(10, 7), sharex=True,
                                      gridspec_kw={"height_ratios": [3, 1]})
    top.plot(kalshi.index, kalshi["hold"] * 100, label="Kalshi")
    top.plot(poly.index, poly["hold"] * 100, label="Polymarket")
    fw = fedwatch_points(meeting)
    if len(fw):
        top.scatter(fw.index, fw.values * 100, color="black", s=15,
                    label="CME FedWatch (hand log)", zorder=3)
    top.axvline(decision, linestyle="--", color="grey")
    top.set_ylabel("P(no change), %")
    top.set_title(f"Market-implied probability the Fed holds, {meeting} meeting")
    top.legend()

    gap = (kalshi["hold"] - poly["hold"]).dropna() * 100
    bottom.bar(gap.index, gap.values, width=1, color="grey")
    bottom.axhline(0, color="black", linewidth=0.8)
    bottom.set_ylabel("Kalshi minus\nPolymarket, pts")

    fig.tight_layout()
    os.makedirs("images", exist_ok=True)
    path = f"images/history_{meeting}.png"
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")


if __name__ == "__main__":
    meeting = sys.argv[1] if len(sys.argv) > 1 else "2026-10"
    build(meeting)
