# Paste into dashboard.py inside your daemon_tabs section.
# This reads real state written by delta_scalp.py — nothing here is a
# hardcoded display value. If delta_state.json doesn't exist yet, it
# shows that honestly instead of a placeholder number.

import json
import os

DELTA_STATE_PATH = "/app/data/delta_state.json"
DELTA_LEDGER_PATH = "/app/data/failures_ledger.json"

daemon_tabs = st.tabs([
    "⚡ Project DELTA (Paper Scalp Engine)",
    # ... your other existing tabs
])

with daemon_tabs[0]:
    st.warning("PAPER TRADING — simulated fills on real live Pionex data. No real orders placed.")

    if os.path.exists(DELTA_STATE_PATH):
        with open(DELTA_STATE_PATH) as f:
            state = json.load(f)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Paper Trades", state.get("total_trades") or 0)
        with col2:
            wr = state.get("win_rate_pct")
            st.metric("Win Rate", f"{wr}%" if wr is not None else "—")
        with col3:
            pnl = state.get("cumulative_pnl_pct")
            st.metric("Cumulative PnL", f"{pnl:+.2f}%" if pnl is not None else "—",
                       delta=None)

        st.caption(f"Status: {state.get('status', 'unknown')} · "
                    f"Symbol: {state.get('symbol', '?')} · "
                    f"Today: {state.get('today_pnl_bps', 0):+.1f} bps")
    else:
        st.info("No data yet — delta_scalp.py hasn't written its first state file. "
                "Check the container logs.")

    st.markdown("**Recent trades (real fills against live prices, wins and losses):**")
    if os.path.exists(DELTA_LEDGER_PATH):
        with open(DELTA_LEDGER_PATH) as f:
            ledger = json.load(f)
        recent = ledger[-20:][::-1]
        if recent:
            st.dataframe(recent, use_container_width=True)
        else:
            st.caption("No trades logged yet.")
    else:
        st.caption("No trade ledger yet.")
