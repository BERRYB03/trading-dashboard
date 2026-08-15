"""
Project DELTA — paper-trading scalp engine.

MODE: PAPER. No real orders are ever sent to Pionex from this file.
All prices used to compute PnL are REAL, live prices pulled from Pionex's
public market data API. Fills are simulated (you didn't actually get
matched), but the market conditions used to price those simulated fills
are not synthetic.

This intentionally logs LOSSES as well as wins. If you look at
delta_ledger.json after running this for a while and every single
trade is a win, that is a bug, not good luck — stop and debug it rather
than trusting it.

Before flipping this to live execution, you need:
  - Real Pionex API key/secret (TRADE permission) via env vars, HMAC-signed
    per https://www.pionex.com/docs/api-docs
  - A validated positive edge from real paper-trading stats over a
    meaningful sample size (hundreds of trades minimum, not a lucky 20)
  - Real fee schedule confirmed from your Pionex account tier
  - Slippage modeling checked against actual fills, not assumed
None of that is implemented here on purpose — that's a separate, higher-
stakes piece of work you should only do after this proves itself honestly.
"""

import json
import os
import time
import traceback

from pionex_client import PionexClient, PionexAPIError
import strategy

DATA_DIR = os.environ.get("DELTA_DATA_DIR", "/app/data")
LEDGER_PATH = os.path.join(DATA_DIR, "delta_ledger.json")
STATE_PATH = os.path.join(DATA_DIR, "delta_state.json")
SYSTEM_STATE_PATH = os.path.join(DATA_DIR, "system_state.json")

SYMBOL = os.environ.get("DELTA_SYMBOL", "SUI_USDT")
SYMBOL_TYPE = os.environ.get("DELTA_SYMBOL_TYPE", "PERP")
POLL_SECONDS = float(os.environ.get("DELTA_POLL_SECONDS", "3"))

# Conservative assumed round-trip cost. VERIFY against your actual Pionex
# fee tier before trusting PnL numbers — this is a placeholder, not a
# looked-up fact about your account.
ASSUMED_FEE_BPS_ROUND_TRIP = float(os.environ.get("DELTA_FEE_BPS", "10"))

MAX_DAILY_LOSS_PCT = float(os.environ.get("DELTA_MAX_DAILY_LOSS_PCT", "3.0"))
LEDGER_KEEP_LAST = 500


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default
    return default


def save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def is_halted() -> bool:
    state = load_json(SYSTEM_STATE_PATH, {})
    return bool(state.get("HALT_TRADING", False))


def today_pnl_bps(ledger: list) -> float:
    today = time.strftime("%Y-%m-%d", time.gmtime())
    return sum(
        t["pnl_bps"] for t in ledger
        if t.get("date") == today
    )


def simulate_trade(client: PionexClient, signal: strategy.Signal) -> dict:
    """
    Simulates holding a position until TP, SL, or max hold time, polling
    REAL prices from Pionex throughout. Returns an honest trade record —
    win or loss, whichever actually happens.
    """
    entry_price = signal.ask_price if signal.side == "BUY" else signal.bid_price
    entry_time = time.time()
    outcome = None
    exit_price = entry_price

    while time.time() - entry_time < strategy.MAX_HOLD_SECONDS:
        time.sleep(POLL_SECONDS)
        try:
            bt = client.get_book_ticker(SYMBOL, SYMBOL_TYPE)
        except PionexAPIError:
            continue  # transient fetch failure; keep holding, don't fabricate a price

        mark = float(bt["bidPrice"]) if signal.side == "BUY" else float(bt["askPrice"])
        move_bps = ((mark - entry_price) / entry_price) * 10_000
        if signal.side == "SELL":
            move_bps = -move_bps

        if move_bps >= strategy.TAKE_PROFIT_BPS:
            outcome, exit_price = "TAKE_PROFIT", mark
            break
        if move_bps <= -strategy.STOP_LOSS_BPS:
            outcome, exit_price = "STOP_LOSS", mark
            break

    if outcome is None:
        outcome, exit_price = "TIME_EXIT", mark if "mark" in dir() else entry_price

    gross_move_bps = ((exit_price - entry_price) / entry_price) * 10_000
    if signal.side == "SELL":
        gross_move_bps = -gross_move_bps

    net_pnl_bps = gross_move_bps - ASSUMED_FEE_BPS_ROUND_TRIP

    return {
        "timestamp": time.time(),
        "date": time.strftime("%Y-%m-%d", time.gmtime()),
        "mode": "PAPER",
        "symbol": SYMBOL,
        "side": signal.side,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "outcome": outcome,               # TAKE_PROFIT | STOP_LOSS | TIME_EXIT
        "gross_pnl_bps": round(gross_move_bps, 2),
        "fee_bps": ASSUMED_FEE_BPS_ROUND_TRIP,
        "pnl_bps": round(net_pnl_bps, 2),  # net of assumed fees — can be negative
        "win": net_pnl_bps > 0,
        "entry_imbalance": signal.imbalance,
        "entry_spread_bps": round(signal.spread_bps, 2),
    }


def update_state(ledger: list, status: str):
    trades = [t for t in ledger if t.get("mode") == "PAPER"]
    n = len(trades)
    wins = sum(1 for t in trades if t["win"])
    total_pnl_bps = sum(t["pnl_bps"] for t in trades)
    state = {
        "mode": "PAPER TRADING — no real orders placed",
        "status": status,
        "symbol": SYMBOL,
        "total_trades": n,
        "win_rate_pct": round(100 * wins / n, 1) if n else None,
        "cumulative_pnl_bps": round(total_pnl_bps, 2),
        "cumulative_pnl_pct": round(total_pnl_bps / 100, 3),
        "today_pnl_bps": round(today_pnl_bps(ledger), 2),
        "last_update": time.time(),
    }
    save_json(STATE_PATH, state)


def run():
    print("[DELTA SCALP] Starting PAPER TRADING engine against live Pionex data.")
    print(f"[DELTA SCALP] Symbol={SYMBOL} type={SYMBOL_TYPE} poll={POLL_SECONDS}s")
    os.makedirs(DATA_DIR, exist_ok=True)
    client = PionexClient()

    while True:
        try:
            if is_halted():
                update_state(load_json(LEDGER_PATH, []), status="HALTED (manual)")
                time.sleep(10)
                continue

            ledger = load_json(LEDGER_PATH, [])

            if today_pnl_bps(ledger) <= -MAX_DAILY_LOSS_PCT * 100:
                print("[DELTA SCALP] Daily loss limit hit. Halting for today.")
                update_state(ledger, status=f"HALTED (daily loss limit -{MAX_DAILY_LOSS_PCT}% hit)")
                time.sleep(60)
                continue

            try:
                bt = client.get_book_ticker(SYMBOL, SYMBOL_TYPE)
            except PionexAPIError as e:
                print(f"[DELTA SCALP] Market data fetch failed: {e}")
                time.sleep(5)
                continue

            signal = strategy.evaluate(bt)
            
            if signal is None:
                bid_size = float(bt.get("bidSize", 0))
                ask_size = float(bt.get("askSize", 0))
                current_imbalance = strategy.compute_imbalance(bid_size, ask_size)
                status_msg = f"Scanning — Imbalance: {current_imbalance:+.2f} (Threshold: ±{strategy.IMBALANCE_THRESHOLD})"
                update_state(ledger, status=status_msg)
                if int(time.time()) % 15 < POLL_SECONDS:
                    print(f"[DELTA SCALP] {status_msg}")
                time.sleep(POLL_SECONDS)
                continue

            print(f"[DELTA SCALP] Signal: {signal.side} imbalance={signal.imbalance:.2f}")
            trade = simulate_trade(client, signal)
            ledger.append(trade)
            save_json(LEDGER_PATH, ledger[-LEDGER_KEEP_LAST:])
            update_state(ledger, status="Scanning — no signal")

            outcome_str = "WIN" if trade["win"] else "LOSS"
            print(f"[DELTA SCALP] Trade closed: {trade['outcome']} → {outcome_str} "
                  f"({trade['pnl_bps']:+.2f} bps net)")

        except Exception:
            print("[DELTA SCALP ERROR]")
            traceback.print_exc()
            time.sleep(5)


if __name__ == "__main__":
    run()
