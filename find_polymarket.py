"""
Find the Polymarket slug for a meeting, to paste into config.py.

Usage:   py find_polymarket.py "fed decision september"
"""

import sys

import sources

query = " ".join(sys.argv[1:]) or "fed decision"
for slug, title, end_date, closed in sources.find_polymarket_slug(query):
    status = "closed" if closed else "open"
    print(f"{title:45s} {str(end_date)[:10]}  {status:6s}  {slug}")
