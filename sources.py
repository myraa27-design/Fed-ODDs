"""
Download data from Kalshi, Polymarket and FRED, and convert each one into
probabilities for the same five outcomes (see OUTCOMES in config.py).

Each "fetch" function talks to the internet. Each "convert" function only does
maths, so you can test it without a connection (see check_math.py).
"""

import io
import json
import time

import pandas as pd
import requests

from config import OUTCOMES, STEP, USE_FRED

KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
GAMMA = "https://gamma-api.polymarket.com"      # Polymarket market info
CLOB = "https://clob.polymarket.com"            # Polymarket price history
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"

# Some sites (FRED especially) hang up on requests that don't look like a browser.
HEADERS = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")}


# ---------------------------------------------------------------- helpers

def get_json(url, params=None):
    """Download a URL and return the JSON response as Python dicts/lists."""
    response = requests.get(url, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()          # stop with an error if the request failed
    return response.json()


def mid_price(bid, ask):
    """Halfway between the best bid and best ask. None if either is missing."""
    if bid is None or ask is None:
        return None
    return (float(bid) + float(ask)) / 2


def as_list(value):
    """Polymarket sometimes sends lists as text like '["Yes", "No"]'. Fix that."""
    if isinstance(value, str):
        return json.loads(value)
    return value


def normalise(probs):
    """Scale a dict of probabilities so they add up to exactly 1."""
    total = sum(probs.values())
    if total == 0:
        return probs
    return {k: v / total for k, v in probs.items()}


# ---------------------------------------------------------------- FRED

def fred_series(series_id, tries=2):
    """Daily FRED series as a DataFrame with columns: date, value."""
    if not USE_FRED:
        raise RuntimeError("FRED switched off in config.py (USE_FRED = False)")
    for attempt in range(tries):
        try:
            response = requests.get(FRED_CSV.format(series_id), headers=HEADERS, timeout=10)
            response.raise_for_status()
            break
        except requests.RequestException:
            if attempt == tries - 1:
                raise                      # give up after the last try
            time.sleep(2)                  # wait 2 seconds, then try again
    df = pd.read_csv(io.StringIO(response.text))
    df.columns = ["date", "value"]                       # first column is the date
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")   # '.' -> NaN
    return df.dropna()


def latest(series_id):
    """Most recent value of a FRED series, e.g. latest('EFFR'). None if FRED fails."""
    try:
        return float(fred_series(series_id)["value"].iloc[-1])
    except Exception as error:
        print(f"  (FRED unavailable for {series_id}: {type(error).__name__})")
        return None


# ---------------------------------------------------------------- converting

def change_to_outcome(change):
    """Map a change in the upper bound (in % points) to one of the five outcomes."""
    steps = round(change / STEP)          # e.g. +0.25 -> 1 step, -0.50 -> -2 steps
    if steps <= -2:
        return "cut_50+"
    if steps == -1:
        return "cut_25"
    if steps == 0:
        return "hold"
    if steps == 1:
        return "hike_25"
    return "hike_50+"


def ladder_to_outcomes(strikes, p_above, current_upper):
    """
    Kalshi -> outcome probabilities.

    strikes:  sorted strike levels, e.g. [3.75, 4.00, 4.25]
    p_above:  P(upper bound > strike) for each strike (mid prices)
    current_upper: today's upper bound of the target range, e.g. 4.00

    P(upper lands exactly on the next strike up) = P(> this one) - P(> next one).
    """
    p = [float(x) for x in p_above]
    for i in range(1, len(p)):            # prices should never rise with the strike;
        p[i] = min(p[i], p[i - 1])        # clean up small bid/ask noise

    levels = {strikes[0]: 1 - p[0]}       # at or below the lowest strike
    for i in range(len(strikes) - 1):
        levels[strikes[i + 1]] = p[i] - p[i + 1]
    levels[strikes[-1] + STEP] = p[-1]    # above the highest strike

    outcomes = {name: 0.0 for name in OUTCOMES}
    for level, prob in levels.items():
        outcomes[change_to_outcome(level - current_upper)] += prob
    return normalise(outcomes)


def question_to_outcome(question):
    """Polymarket question text -> outcome name (None if it can't tell)."""
    q = question.lower()
    if "no change" in q:
        return "hold"
    big = "50+" in q
    if "decrease" in q or " cut" in q:
        return "cut_50+" if big else "cut_25"
    if "increase" in q or "hike" in q:
        return "hike_50+" if big else "hike_25"
    return None


# ---------------------------------------------------------------- Kalshi

def kalshi_markets(event_ticker):
    """Live Kalshi ladder for one meeting: ticker, strike, bid, ask, mid."""
    data = get_json(f"{KALSHI}/markets", {"event_ticker": event_ticker, "limit": 100})
    rows = []
    for m in data["markets"]:
        bid = m.get("yes_bid_dollars")
        ask = m.get("yes_ask_dollars")
        rows.append({
            "ticker": m["ticker"],
            "strike": float(m["floor_strike"]),
            "bid": float(bid) if bid is not None else None,
            "ask": float(ask) if ask is not None else None,
            "mid": mid_price(bid, ask),
        })
    return pd.DataFrame(rows).sort_values("strike").reset_index(drop=True)


def kalshi_now(event_ticker, current_upper):
    """Live Kalshi outcome probabilities for one meeting."""
    ladder = kalshi_markets(event_ticker).dropna(subset=["mid"])
    return ladder_to_outcomes(list(ladder["strike"]), list(ladder["mid"]), current_upper)


def kalshi_candles(ticker, start_ts, end_ts):
    """Daily mid prices for one Kalshi strike. Returns a Series indexed by date."""
    path = f"/series/KXFED/markets/{ticker}/candlesticks"
    params = {"start_ts": start_ts, "end_ts": end_ts, "period_interval": 1440}
    try:
        data = get_json(KALSHI + path, params)
    except requests.HTTPError:
        # Markets that settled a while ago live under /historical
        data = get_json(f"{KALSHI}/historical/markets/{ticker}/candlesticks", params)
    return candles_to_series(data)


def candles_to_series(data):
    """Kalshi candlestick JSON -> Series of daily mid prices (convert step)."""
    values = {}
    for c in data.get("candlesticks", []):
        bid = (c.get("yes_bid") or {}).get("close_dollars")
        ask = (c.get("yes_ask") or {}).get("close_dollars")
        mid = mid_price(bid, ask)
        if mid is not None:
            day = pd.to_datetime(c["end_period_ts"], unit="s").normalize()
            values[day] = mid
    return pd.Series(values, dtype=float).sort_index()


# ---------------------------------------------------------------- Polymarket

def polymarket_markets(slug):
    """Live Polymarket markets for one meeting: outcome, price, mid, token id."""
    event = get_json(f"{GAMMA}/events", {"slug": slug})[0]
    rows = []
    for m in event["markets"]:
        outcome = question_to_outcome(m["question"])
        if outcome is None:
            continue
        yes_price = float(as_list(m["outcomePrices"])[0])
        mid = mid_price(m.get("bestBid"), m.get("bestAsk"))
        rows.append({
            "outcome": outcome,
            "question": m["question"],
            "price": yes_price,
            "mid": mid if mid is not None else yes_price,
            "yes_token": as_list(m["clobTokenIds"])[0],
        })
    return pd.DataFrame(rows)


def polymarket_now(slug):
    """Live Polymarket outcome probabilities for one meeting."""
    df = polymarket_markets(slug)
    probs = {name: 0.0 for name in OUTCOMES}
    for _, row in df.iterrows():
        probs[row["outcome"]] += row["mid"]
    return normalise(probs)


def polymarket_history(token_id):
    """Daily price history for one Polymarket outcome. Series indexed by date."""
    data = get_json(f"{CLOB}/prices-history",
                    {"market": token_id, "interval": "max", "fidelity": 1440})
    return history_to_series(data)


def history_to_series(data):
    """Polymarket prices-history JSON -> Series (last price of each day)."""
    points = data.get("history", [])
    if not points:
        return pd.Series(dtype=float)
    df = pd.DataFrame(points)
    df["day"] = pd.to_datetime(df["t"], unit="s").dt.normalize()
    return df.groupby("day")["p"].last().astype(float)


def find_polymarket_slug(query):
    """Search Polymarket events, e.g. find_polymarket_slug('fed decision december')."""
    data = get_json(f"{GAMMA}/public-search", {"q": query, "limit_per_type": 10})
    return [(e["slug"], e["title"], e.get("endDate"), e.get("closed"))
            for e in data.get("events", [])]
