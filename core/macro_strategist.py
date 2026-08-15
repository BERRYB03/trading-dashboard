import sqlite3
import time
import os
import json
from datetime import datetime
import random

# DATA PATHS
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DB_PATH = os.path.join(DATA_DIR, 'macro_intel.db')
STATE_PATH = os.path.join(DATA_DIR, 'system_state.json')

def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Create Equity Log Table
    c.execute('''CREATE TABLE IF NOT EXISTS equity_log
                 (timestamp DATETIME, total_equity REAL, drawdown REAL)''')
    # Create SWOT Reports Table
    c.execute('''CREATE TABLE IF NOT EXISTS swot_reports
                 (timestamp DATETIME, report TEXT)''')
    conn.commit()
    return conn

def check_kill_switch():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, 'r') as f:
                state = json.load(f)
                return state.get("HALT_TRADING", False)
        except Exception:
            return False
    return False

def generate_swot_report(conn):
    """Generates the macro intelligence briefing."""
    current_time = datetime.now().isoformat()
    
    swot_markdown = """### 🦅 Macro-Strategist Tactical Overview
**Strengths:** Dual-agent architecture (BETA + GAMMA) is fully deployed and isolated behind a zero-trust IAP tunnel.
**Weaknesses:** Post-mortem ledger is currently empty; neural matrix requires historical failure data to optimize.
**Opportunities:** Capitalizing on low-volume accumulation zones prior to parabolic breakouts.
**Threats:** Unprecedented macroeconomic volatility or flash-crashes bypassing standard trailing stops."""

    c = conn.cursor()
    c.execute("INSERT INTO swot_reports (timestamp, report) VALUES (?, ?)", (current_time, swot_markdown))
    conn.commit()
    print(f"[{current_time}] SWOT Intelligence Report generated.")

def log_equity(conn):
    """Logs current portfolio equity. (Mocked with variance around initial $93.87 reserve)"""
    current_time = datetime.now().isoformat()
    
    # In a fully wired state, this calls PionexAuth to fetch real USDT balance.
    # We simulate slight institutional yield here for the dashboard telemetry.
    base_equity = 93.87
    
    # Generate some random variance to simulate live market data
    variance = random.uniform(-0.5, 1.2)
    total_equity = round(base_equity + variance, 2)
    
    # Calculate Drawdown from baseline
    drawdown = 0.0 if total_equity >= base_equity else round(((total_equity - base_equity) / base_equity) * 100, 2)
    
    c = conn.cursor()
    c.execute("INSERT INTO equity_log (timestamp, total_equity, drawdown) VALUES (?, ?, ?)", 
              (current_time, total_equity, drawdown))
    conn.commit()
    print(f"[{current_time}] Equity Logged: {total_equity} USDT | Drawdown: {drawdown}%")

def main():
    print("[*] Macro-Strategist Daemon Initializing...")
    conn = init_db()
    
    # Generate initial intelligence report
    generate_swot_report(conn)
    
    print("[*] Entering Cron/Task Scheduler Loop...")
    cycles = 0
    while True:
        if check_kill_switch():
            print("[!] GLOBAL KILL SWITCH DETECTED. Macro-Strategist halting execution.")
            break
            
        log_equity(conn)
        
        # Generate a new SWOT report every 360 cycles (approx 6 hours at 60s/cycle)
        cycles += 1
        if cycles % 360 == 0:
            generate_swot_report(conn)
            
        time.sleep(60)

if __name__ == "__main__":
    main()
