"""
Order Book Imbalance (OBI) scalping strategy.

This computes a real signal from real depth data. It does NOT guarantee
a win — imbalance is a genuine but noisy microstructure signal, and this
will produce losing trades. That's expected and correct; a strategy spec
that never loses is a sign something is fake, not a sign it's good.

Tune IMBALANCE_THRESHOLD, TAKE_PROFIT_BPS, STOP_LOSS_BPS against your own
backtests before trusting this. The defaults here are reasonable starting
points, not a validated edge.
"""

from dataclasses import dataclass
from typing import Optional

IMBALANCE_THRESHOLD = 0.35   # top-of-book imbalance required to trigger a signal
TAKE_PROFIT_BPS = 8          # exit target, in basis points of entry price
STOP_LOSS_BPS = 6            # exit stop, in basis points of entry price
MAX_HOLD_SECONDS = 90        # force-exit if neither TP nor SL hit in time


@dataclass
class Signal:
    side: str          # "BUY" or "SELL"
    imbalance: float
    bid_price: float
    ask_price: float
    spread_bps: float


def compute_imbalance(bid_size: float, ask_size: float) -> float:
    """Range [-1, 1]. Positive = more resting buy interest than sell."""
    total = bid_size + ask_size
    if total == 0:
        return 0.0
    return (bid_size - ask_size) / total


def evaluate(book_ticker: dict) -> Optional[Signal]:
    """
    Takes a real book_ticker dict from PionexClient.get_book_ticker() and
    returns a Signal if the imbalance crosses the threshold, else None.
    """
    bid_price = float(book_ticker["bidPrice"])
    ask_price = float(book_ticker["askPrice"])
    bid_size = float(book_ticker["bidSize"])
    ask_size = float(book_ticker["askSize"])

    if bid_price <= 0 or ask_price <= 0:
        return None

    mid = (bid_price + ask_price) / 2
    spread_bps = ((ask_price - bid_price) / mid) * 10_000

    imbalance = compute_imbalance(bid_size, ask_size)

    if imbalance >= IMBALANCE_THRESHOLD:
        return Signal("BUY", imbalance, bid_price, ask_price, spread_bps)
    if imbalance <= -IMBALANCE_THRESHOLD:
        return Signal("SELL", imbalance, bid_price, ask_price, spread_bps)
    return None
