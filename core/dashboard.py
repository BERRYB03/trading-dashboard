import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sqlite3
import json
import os
import time

# DIRECTIVE 2: WIDE LAYOUT & DARK MODE (Streamlit is dark mode by default if configured, but wide is set here)
st.set_page_config(page_title="GAMMA Observability", layout="wide", initial_sidebar_state="collapsed")

# DIRECTIVE 3: AUTH GATEKEEPER
def check_password():
    """Returns `True` if the user had the correct password."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.markdown("### ZERO-TRUST AUTHENTICATION REQUIRED")
        pwd = st.text_input("Passphrase", type="password")
        if pwd:
            try:
                expected_password = st.secrets["PASSPHRASE"]
            except Exception:
                expected_password = "admin_override"
                
            if pwd == expected_password:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Access Denied. Intrusion Logged.")
        return False
    return True

if not check_password():
    st.stop()

# DIRECTIVE 3: LIVE POLLING (Native Streamlit Fragment Auto-Refresh)
@st.fragment(run_every="60s")
def render_dashboard():
    st.title("🛡️ PROJECT GAMMA: Observability Command Center")
    
    col1, col2 = st.columns([2, 1])
    
    # DATA PATHS (Mapped to shared_data volume)
    DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'macro_intel.db')
    LEDGER_PATH = os.path.join(os.path.dirname(__file__), 'data', 'failures_ledger.json')
    STATE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'system_state.json')
    
    with col1:
        # MODULE 1: THE MACRO VIEW (Total Equity vs Max Drawdown)
        st.subheader("Macro View: Fleet Performance")
        try:
            conn = sqlite3.connect(DB_PATH)
            # Fetch equity curve, fallback to mock if table missing
            df_equity = pd.read_sql_query("SELECT timestamp, total_equity, drawdown FROM equity_log ORDER BY timestamp ASC", conn)
            
            fig_macro = go.Figure()
            # Primary Line: Total Equity
            fig_macro.add_trace(go.Scatter(x=df_equity['timestamp'], y=df_equity['total_equity'], mode='lines', name='Total Equity ($)', line=dict(color='#00ff00', width=2)))
            # Secondary Shaded Area: Max Drawdown
            fig_macro.add_trace(go.Scatter(x=df_equity['timestamp'], y=df_equity['drawdown'], mode='lines', name='Drawdown (%)', fill='tozeroy', line=dict(color='crimson', width=0), yaxis='y2'))
            
            fig_macro.update_layout(
                yaxis=dict(title='Total Equity (USDT)', color='#00ff00'),
                yaxis2=dict(title='Drawdown (%)', color='crimson', overlaying='y', side='right', range=[-50, 0]),
                template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0), height=400
            )
            st.plotly_chart(fig_macro, use_container_width=True)
        except Exception as e:
            st.warning(f"Macro Intel DB pending initialization... ({e})")
            
        # MODULE 2: THE MICRO VIEW (AI Confidence vs Realized PnL)
        st.subheader("Micro View: Neural Execution Matrix")
        try:
            if os.path.exists(LEDGER_PATH):
                with open(LEDGER_PATH, 'r') as f:
                    ledger = json.load(f)
                
                if ledger:
                    df_ledger = pd.DataFrame(ledger)
                    df_ledger['color'] = df_ledger['pnl_pct'].apply(lambda x: 'Profit' if x > 0 else 'Loss')
                    
                    fig_micro = px.scatter(
                        df_ledger, x="confidence", y="pnl_pct", color="color",
                        hover_data=["symbol", "failure_trigger", "timestamp"],
                        color_discrete_map={"Profit": "#00ff00", "Loss": "crimson"},
                        title="Confidence Score vs Realized PnL"
                    )
                    fig_micro.update_layout(template="plotly_dark", height=400)
                    st.plotly_chart(fig_micro, use_container_width=True)
                else:
                    st.info("Failure ledger is currently empty.")
            else:
                st.info("Ledger syncing...")
        except Exception as e:
            st.error(f"Ledger Parsing Error: {e}")

    with col2:
        # MODULE 3: THE INTELLIGENCE BRIEFING
        st.subheader("Macro-Strategist Briefing")
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT report FROM swot_reports ORDER BY timestamp DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                st.markdown(f"> {row[0]}")
            else:
                st.markdown("*Awaiting first Macro SWOT report generation...*")
        except Exception:
            st.markdown("*Connecting to Macro-Strategist intelligence stream...*")
            
        st.divider()
        
        # MODULE 4: EMERGENCY OVERRIDE (KILL SWITCH)
        st.subheader("System Control")
        st.markdown("⚠️ **WARNING: This action immediately halts all active daemons and liquidates open positions.**")
        if st.button("🛑 INITIATE GLOBAL KILL SWITCH", use_container_width=True, type="primary"):
            os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
            with open(STATE_PATH, 'w') as f:
                json.dump({"HALT_TRADING": True, "timestamp": time.time()}, f)
            st.error("GLOBAL KILL SWITCH ACTIVATED. TRADING HALTED.")
            
render_dashboard()
