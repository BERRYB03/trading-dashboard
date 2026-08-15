# Project DELTA — Paper Scalp Engine

## What this actually is
- Market data: **real**, pulled live from Pionex's public REST API
  (`/api/v1/market/bookTickers`, no API key needed).
- Strategy: order book imbalance (OBI) — a real, documented microstructure
  signal, not guaranteed to be profitable. Tune it, backtest it, don't
  trust the defaults blindly.
- Fills: **simulated**. No orders are sent to Pionex. Fill price is the
  real live bid/ask at signal time; exit is tracked against real live
  prices until TP/SL/timeout.
- PnL: net of an *assumed* fee (`DELTA_FEE_BPS`, default 10 bps
  round-trip) — verify this against your real Pionex fee tier and update
  the env var.
- Logging: every trade is logged — wins and losses both. If you ever see
  a 100% win rate over more than a handful of trades, something is
  broken; stop and check the code, don't deploy it further.

## Deploy
1. Drop `pionex_client.py`, `strategy.py`, `delta_scalp.py`,
   `Dockerfile.delta` into your repo root.
2. Merge `docker-compose.snippet.yml`'s `delta_scalp:` block into your
   existing `docker-compose.yml`.
3. Paste `dashboard_delta_tab.py`'s content into `dashboard.py`.
4. `git pull origin main && docker compose down --remove-orphans && docker compose up -d --build`

## Reading the results honestly
- Let it run for at minimum a few hundred trades before drawing any
  conclusion. Under ~50 trades, win rate is mostly noise.
- Look at `cumulative_pnl_bps` net of fees, not just win rate — a 60% win
  rate with a bad risk/reward can still lose money.
- `HALT_TRADING: true` in `system_state.json` stops it; the daily loss
  limit (`DELTA_MAX_DAILY_LOSS_PCT`) also auto-halts for the day.

## What's deliberately NOT built yet
Going live means sending real signed orders with real capital. That
needs, at minimum:
- Pionex API key/secret with TRADE permission, HMAC-signed requests
- Confirmed real fee schedule for your account tier
- Order execution + partial-fill handling + real slippage measurement
- A paper track record that's actually good, measured honestly

That's a separate, higher-stakes build. Don't wire it up until the
paper numbers above earn it.
