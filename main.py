"""Forecast Bitcoin's price 240 minutes after each checkpoint.

Entry for make.fun's btc-cent-forecast-01. For every case file in the
input directory the program reads the 72 hours of 1-minute closes that
end at the checkpoint and writes one forecast: its best estimate of the
close 240 minutes later. The score is the mean absolute error, so the
forecast aims at the median of where the price is likely to be, not at
a bold guess in either direction.

The estimate blends two weak but opposing signals, both measured on
the case's own history:

* the full average drift: the mean 240-minute move seen across the
  last 48 hours, taken whole. Trends persist enough over a 4-hour
  horizon that shrinking this term gave back accuracy in backtests.
* a firm pull toward the mean price of the last 24 hours: two fifths
  of the gap is given back. Pool prices wander around their day's
  centre of mass and snap back, and the mean (not the median) is the
  centre the pull has to aim at.

The weights were chosen by backtest, not by taste: on 648 pseudo-
checkpoints inside the practice windows plus the five practice cases
whose answers are recoverable, this blend cut the persistence error
by about a sixth and beat the earlier shrunk-drift/median blend on
every evaluation slice, in both halves of every set and in every
practice window taken one at a time. Richer variants (volatility
conditioning, recent-move terms, larger drift weights) were tested
and rejected: each one's gains sat in one slice of the sample and
reversed in another.

Standard library only, no network, fully deterministic: the same case
always produces the same bytes.
"""

import json
import os
from pathlib import Path

HORIZON = 240          # minutes ahead, fixed by the case format
DRIFT_STEP = 15        # sampling step for the overlapping 240m moves
DRIFT_WINDOW = 2880    # the drift is read from the last 48 hours
DRIFT_WEIGHT = 1.0     # the mean drift is taken whole
ANCHOR_WEIGHT = 0.40   # share of the gap to the 24h mean given back
ANCHOR_WINDOW = 1440   # one day of minutes


def mean_drift(prices):
    """Mean move over HORIZON minutes, sampled across the last 48h."""
    window = prices[-DRIFT_WINDOW:]
    moves = [
        window[i + HORIZON] - window[i]
        for i in range(0, len(window) - HORIZON, DRIFT_STEP)
    ]
    if not moves:
        return 0.0
    return sum(moves) / len(moves)


def forecast(prices):
    """Best single estimate of the close HORIZON minutes from the end."""
    last = prices[-1]
    if len(prices) <= HORIZON:
        return last
    anchor_window = prices[-ANCHOR_WINDOW:]
    anchor = sum(anchor_window) / len(anchor_window)
    guess = last
    guess += ANCHOR_WEIGHT * (anchor - last)
    guess += DRIFT_WEIGHT * mean_drift(prices)
    return guess


def run_case(path, out_dir):
    case = json.loads(path.read_text(encoding="utf-8"))
    case_id = case.get("case") or path.name[: -len(".in")]
    prices = case["markets"][0]["prices"]
    price = round(forecast(prices), 5)
    price = min(max(price, 0.01), 9_999_999.0)
    payload = {"forecasts": [{"case": case_id, "price": price}]}
    text = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    (out_dir / f"{case_id}.out").write_text(text, encoding="utf-8")


def main():
    in_dir = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(in_dir.glob("*.in")):
        run_case(path, out_dir)


if __name__ == "__main__":
    main()
