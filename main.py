"""Forecast Bitcoin's price 240 minutes after each checkpoint.

Entry for make.fun's btc-cent-forecast-01. For every case file in the
input directory the program reads the 72 hours of 1-minute closes that
end at the checkpoint and writes one forecast: its best estimate of the
close 240 minutes later. The score is the mean absolute error, so the
forecast aims at the median of where the price is likely to be, not at
a bold guess in either direction.

The estimate blends two weak but opposing signals, both measured on
the case's own history:

* a shrunk drift: about two thirds of the mean 240-minute move seen
  across the last 48 hours. Trends persist a little, but the full
  average move over-shoots, so only part of it is added.
* a gentle pull toward the median price of the last 24 hours. Pool
  prices wander and snap back; a quarter of the distance to that
  median is given back.

On top of the last close the two adjustments are small next to the
typical 4-hour move, which is the point: they shave the error of the
persistence guess without ever betting the forecast on a pattern.

Standard library only, no network, fully deterministic: the same case
always produces the same bytes.
"""

import json
import os
import statistics
from pathlib import Path

HORIZON = 240          # minutes ahead, fixed by the case format
DRIFT_STEP = 15        # sampling step for the overlapping 240m moves
DRIFT_WINDOW = 2880    # the drift is read from the last 48 hours
DRIFT_SHRINK = 0.65    # keep about two thirds of the average drift
REVERT_WEIGHT = 0.25   # share of the gap to the 24h median given back
REVERT_WINDOW = 1440   # one day of minutes


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
    anchor = statistics.median(prices[-REVERT_WINDOW:])
    guess = last
    guess += REVERT_WEIGHT * (anchor - last)
    guess += DRIFT_SHRINK * mean_drift(prices)
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
