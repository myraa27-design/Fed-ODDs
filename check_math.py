"""
Offline checks: confirms the conversion maths gives the answers worked out by
hand in the project plan. No internet needed.   py check_math.py
"""

from fedwatch_calc import (change_to_probabilities, expected_change_clean_month,
                           expected_change_meeting_month)
from sources import ladder_to_outcomes, normalise, question_to_outcome


def close(a, b, tol=1e-3):
    return abs(a - b) < tol


# 1. Kalshi ladder, October mid prices on Oct 15 (current upper bound 4.00%)
strikes = [2.75, 3.00, 3.25, 3.50, 3.75, 4.00, 4.25, 4.50, 4.75, 5.00, 5.25]
mids    = [0.995, 0.995, 0.995, 0.995, 0.995, 0.28, 0.005, 0.005, 0.005, 0.005, 0.005]
k = ladder_to_outcomes(strikes, mids, current_upper=4.00)
assert close(k["hold"], 0.715), k
assert close(k["hike_25"], 0.275), k
print("Kalshi ladder:", {n: round(p, 3) for n, p in k.items()})

# 2. Polymarket questions map to the right outcomes
assert question_to_outcome("Will there be no change in Fed interest rates after the October 2026 meeting?") == "hold"
assert question_to_outcome("Will the Fed increase interest rates by 25 bps after the October 2026 meeting?") == "hike_25"
assert question_to_outcome("Will the Fed decrease interest rates by 50+ bps after the October 2026 meeting?") == "cut_50+"
p = normalise({"cut_50+": 0.0015, "cut_25": 0.0035, "hold": 0.705, "hike_25": 0.285, "hike_50+": 0.0055})
assert close(sum(p.values()), 1.0)
print("Polymarket:   ", {n: round(v, 3) for n, v in p.items()})

# 3. Futures, clean month: EFFR 3.83, Nov ZQ 96.10 -> +7 bp -> 28% hike
change = expected_change_clean_month(96.10, 3.83)
assert close(change, 7.0, 0.01), change
probs = change_to_probabilities(change)
assert close(probs["hike_25"], 0.28) and close(probs["hold"], 0.72), probs
print("Futures:      ", {n: round(v, 3) for n, v in probs.items()})

# 4. Futures, meeting month: a fully priced hike should come back as +25 bp
avg = 4.00 * 9 / 31 + 4.25 * 22 / 31
assert close(expected_change_meeting_month(100 - avg, 4.00, 9, 2026, 12), 25.0, 0.01)

# 5. A priced cut: -30 bp -> 80% cut 25, 20% cut 50+
probs = change_to_probabilities(-30)
assert close(probs["cut_25"], 0.8) and close(probs["cut_50+"], 0.2), probs

print("\nAll checks passed.")
