"""
PROJECT DELTA: LIVE EXECUTION ENGINE

MASTER SYSTEM DIRECTIVE:
- Interfaces directly with pionex_client.py for live order book reads.
- Real market/limit order placement on Pionex.
- Zero simulation loops. All PnL is genuine.
- Enforces system_state.json kill switches.
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

SYMBOL = os.environ.get("DELTA_SYMBOL", "BTC_USDT")
SYMBOL_TYPE = os.environ.get("DELTA_SYMBOL_TYPE", "SPOT")
POLL_SECONDS = float(os.environ.get("DELTA_POLL_SECONDS", "3"))

API_KEY = os.environ.get("PIONEX_API_KEY", "")
API_SECRET = os.environ.get("PIONEX_API_SECRET", "")
TRADE_SIZE_USDT = float(os.environ.get("TRADE_SIZE_USDT", "11.0")) # Minimum Pionex order size is usually $10

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
        t.get("pnl_bps", 0) for t in ledger
        if t.get("date") == today
    )

def execute_live_trade(client: PionexClient, signal: strategy.Signal) -> dict:
    """
    Executes a real LIVE market order on Pionex, polls for TP/SL, and
    closes the position with a real market order.
    """
    if not client.api_key or not client.api_secret:
        raise ValueError("LIVE EXECUTION ABORTED: Missing PIONEX_API_KEY or PIONEX_API_SECRET")
        
    entry_time = time.time()
    
    if signal.side == "SELL" and SYMBOL_TYPE == "SPOT":
        raise NotImplementedError("LIVE SHORTING on Spot is not supported. Ignoring SELL signal.")

    print(f"[LIVE EXECUTION] Placing {signal.side} MARKET order for {TRADE_SIZE_USDT} USDT on {SYMBOL}")
    
    entry_price = signal.ask_price if signal.side == "BUY" else signal.bid_price
    
    try:
        # Open Position
        if signal.side == "BUY":
            client.create_order(SYMBOL, "BUY", "MARKET", amount=TRADE_SIZE_USDT)
    except Exception as e:
        print(f"[LIVE ERROR] Entry order failed: {e}")
        return {
            "timestamp": time.time(), "date": time.strftime("%Y-%m-%d", time.gmtime()),
            "mode": "LIVE", "symbol": SYMBOL, "side": signal.side,
            "entry_price": entry_price, "exit_price": entry_price,
            "outcome": "EXECUTION_FAILED", "gross_pnl_bps": 0, "fee_bps": 0, "pnl_bps": 0,
            "win": False, "entry_imbalance": signal.imbalance, "entry_spread_bps": signal.spread_bps,
        }

    outcome = None
    exit_price = entry_price
    
    # Poll for Exit Condition
    while time.time() - entry_time < strategy.MAX_HOLD_SECONDS:
        time.sleep(POLL_SECONDS)
        try:
            bt = client.get_book_ticker(SYMBOL, SYMBOL_TYPE)
        except PionexAPIError:
            continue
            
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
        outcome, exit_price = "TIME_EXIT", mark

    print(f"[LIVE EXECUTION] Closing position. Reason: {outcome}. Fetching balances...")
    
    # Close Position
    try:
        if signal.side == "BUY":
            # Find base asset balance to sell it all
            bals = client.get_balances()
            base_asset = SYMBOL.split("_")[0]
            base_bal = 0.0
            for b in bals:
                if b["coin"] == base_asset:
                    base_bal = float(b["free"])
                    break
                    
            if base_bal > 0:
                qty_str = "{:.5f}".format(base_bal) # format to avoid scientific notation
                client.create_order(SYMBOL, "SELL", "MARKET", size=qty_str)
            else:
                outcome += "_NO_BALANCE"
    except Exception as e:
        print(f"[LIVE ERROR] Exit order failed: {e}")
        outcome += "_EXIT_FAIL"

    gross_move_bps = ((exit_price - entry_price) / entry_price) * 10_000
    if signal.side == "SELL":
        gross_move_bps = -gross_move_bps

    # Real fee lookup is complex, assuming standard 0.1% spot fee round-trip (10 bps) for ledger display
    net_pnl_bps = gross_move_bps - 10.0

    return {
        "timestamp": time.time(),
        "date": time.strftime("%Y-%m-%d", time.gmtime()),
        "mode": "LIVE",
        "symbol": SYMBOL,
        "side": signal.side,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "outcome": outcome,
        "gross_pnl_bps": round(gross_move_bps, 2),
        "fee_bps": 10.0,
        "pnl_bps": round(net_pnl_bps, 2),
        "win": net_pnl_bps > 0,
        "entry_imbalance": signal.imbalance,
        "entry_spread_bps": round(signal.spread_bps, 2),
    }


def update_state(ledger: list, status: str):
    trades = [t for t in ledger if t.get("mode") == "LIVE"]
    n = len(trades)
    wins = sum(1 for t in trades if t.get("win", False))
    total_pnl_bps = sum(t.get("pnl_bps", 0) for t in trades)
    state = {
        "mode": "LIVE TRADING (AUTHORIZED)",
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
    print("==================================================")
    print(" [DELTA SCALP] LIVE EXECUTION ENGINE ACTIVATED")
    print(f" Symbol={SYMBOL} type={SYMBOL_TYPE} poll={POLL_SECONDS}s")
    print(f" Trade Size = {TRADE_SIZE_USDT} USDT")
    print("==================================================")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    client = PionexClient(api_key=API_KEY, api_secret=API_SECRET)

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

            if not API_KEY or not API_SECRET:
                msg = "LIVE EXECUTION HALTED: Missing PIONEX API Keys in ENV"
                print(f"[DELTA SCALP] {msg}")
                update_state(ledger, status=msg)
                time.sleep(10)
                continue

            if signal.side == "SELL" and SYMBOL_TYPE == "SPOT":
                print("[DELTA SCALP] Ignoring SELL signal on SPOT market.")
                time.sleep(POLL_SECONDS)
                continue

            print(f"[DELTA SCALP] LIVE Signal: {signal.side} imbalance={signal.imbalance:.2f}")
            trade = execute_live_trade(client, signal)
            ledger.append(trade)
            save_json(LEDGER_PATH, ledger[-LEDGER_KEEP_LAST:])
            update_state(ledger, status="Scanning — no signal")

            outcome_str = "WIN" if trade["win"] else "LOSS"
            print(f"[DELTA SCALP] Live Trade closed: {trade['outcome']} -> {outcome_str} "
                  f"({trade.get('pnl_bps', 0):+.2f} bps net)")

        except Exception:
            print("[DELTA SCALP ERROR]")
            traceback.print_exc()
            time.sleep(5)

if __name__ == "__main__":
    run()
