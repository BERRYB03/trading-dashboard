import sys

with open('core/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_line = '    daemon_tabs = st.tabs(["🤖 Market Makers (BETA)", "🎯 High-Frequency Sniper (GAMMA)", "🧠 Macro Strategist", "🛡️ Intel Dashboard"])'
new_line = '    daemon_tabs = st.tabs(["🤖 Market Makers (BETA)", "🎯 High-Frequency Sniper (GAMMA)", "🧠 Macro Strategist", "🛡️ Intel Dashboard", "📈 Project DELTA (Paper Scalp)"])'

if old_line in content:
    content = content.replace(old_line, new_line)
else:
    print('Could not find old_line')
    sys.exit(1)

delta_code = """
    with daemon_tabs[4]:
        st.warning("PAPER TRADING — simulated fills on real live Pionex data. No real orders placed.")
        
        DELTA_STATE_PATH = os.path.join(DATA_DIR, 'delta_state.json')
        DELTA_LEDGER_PATH = os.path.join(DATA_DIR, 'failures_ledger.json')

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
                st.metric("Cumulative PnL", f"{pnl:+.2f}%" if pnl is not None else "—", delta=None)

            st.caption(f"Status: {state.get('status', 'unknown')} | Symbol: {state.get('symbol', '?')} | Today: {state.get('today_pnl_bps', 0):+.1f} bps")
        else:
            st.info("No data yet — delta_scalp.py hasn't written its first state file. Check the container logs.")

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
"""

parts = content.rsplit('# Execute Dashboard Render\nrender_command_center()', 1)
new_content = parts[0] + delta_code + '\n# Execute Dashboard Render\nrender_command_center()'

with open('core/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Successfully patched dashboard.py')
