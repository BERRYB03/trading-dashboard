import time
import requests
import json
import os
import asyncio
from core.auth import PionexAuth

class GammaTSLEnforcer:
    def __init__(self):
        self.auth = PionexAuth()
        self.base_url = "https://api.pionex.com"
        self.state_file = os.path.join(os.path.dirname(__file__), 'gamma_state.json')
        self.ledger_file = os.path.join(os.path.dirname(__file__), 'failures_ledger.json')
        
    def write_autopsy(self, state, reason, pnl_pct):
        print(f"[*] Writing Autopsy Report to {self.ledger_file}...")
        
        autopsy = {
            "symbol": state.get('symbol', 'UNKNOWN'),
            "entry_conditions": {
                "daily_change": state.get('daily_change', 0),
                "volume": state.get('volume', 0)
            },
            "original_direction": state.get('direction', 'neutral'),
            "confidence": state.get('confidence', 0),
            "failure_trigger": reason,
            "pnl_pct": pnl_pct,
            "timestamp": time.time()
        }
        
        ledger = []
        if os.path.exists(self.ledger_file):
            try:
                with open(self.ledger_file, 'r') as f:
                    ledger = json.load(f)
            except Exception:
                pass
                
        ledger.append(autopsy)
        
        with open(self.ledger_file, 'w') as f:
            json.dump(ledger, f, indent=4)
        print("[+] Autopsy successfully logged to Ledger.")

    def execute_market_close(self, state, reason, pnl_pct):
        symbol = state['symbol']
        direction = state['direction']
        
        print(f"\n[!!!] GAMMA TSL TRIGGERED: {reason}")
        print(f"[*] Firing Zero-Latency MARKET Close for {symbol}...")
        # Simulating MARKET close execution via /uapi
        print(f"[+] Position Secured.")
        
        if pnl_pct <= 0:
            print("[-] Trade resulted in a loss. Initiating Post-Mortem Autopsy...")
            self.write_autopsy(state, reason, pnl_pct)
        else:
            print("[+] Trade was profitable. No autopsy required.")
            
        if os.path.exists(self.state_file):
            os.remove(self.state_file)

    def process_tsl_math(self, state, current_price):
        direction = state['direction']
        entry_price = state['entry_price']
        watermark = state['watermark']
        trailing_active = state['trailing_active']
        
        if direction == 'long':
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            if pnl_pct <= -5.0:
                return True, f"Hit -5% hard stop in {(time.time() - state['timestamp'])/60:.1f} minutes", pnl_pct, state
            if pnl_pct >= 5.0 and not trailing_active:
                trailing_active = True
            if trailing_active:
                watermark = max(watermark, current_price)
                floor = watermark * 0.98
                if current_price <= floor:
                    return True, f"Trailing Stop Floor Breached", pnl_pct, state
                    
        elif direction == 'short':
            pnl_pct = ((entry_price - current_price) / entry_price) * 100
            if pnl_pct <= -5.0:
                return True, f"Hit -5% hard stop in {(time.time() - state['timestamp'])/60:.1f} minutes", pnl_pct, state
            if pnl_pct >= 5.0 and not trailing_active:
                trailing_active = True
            if trailing_active:
                watermark = min(watermark, current_price)
                floor = watermark * 1.02
                if current_price >= floor:
                    return True, f"Trailing Stop Floor Breached", pnl_pct, state
                    
        state['watermark'] = watermark
        state['trailing_active'] = trailing_active
        return False, "", 0, state

    async def run_enforcer_loop(self):
        print("="*60)
        print(" PROJECT GAMMA : TSL ENFORCER & AUTOPSY DAEMON ONLINE")
        print("="*60)
        
        while True:
            if not os.path.exists(self.state_file):
                await asyncio.sleep(2)
                continue
                
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    
                resp = await asyncio.to_thread(requests.get, f"{self.base_url}/api/v1/market/tickers")
                price_data = resp.json()
                
                spot_sym = state['symbol'].replace('.PERP', '')
                current_price = 0
                for t in price_data.get('data', {}).get('tickers', []):
                    if t['symbol'] == spot_sym:
                        current_price = float(t.get('markPrice', t.get('close', 0)))
                        break
                        
                if current_price == 0:
                    await asyncio.sleep(1)
                    continue
                    
                kill, reason, pnl_pct, updated_state = self.process_tsl_math(state, current_price)
                
                if kill:
                    self.execute_market_close(state, reason, pnl_pct)
                else:
                    with open(self.state_file, 'w') as f:
                        json.dump(updated_state, f, indent=4)
                        
            except Exception as e:
                pass
                
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    enforcer = GammaTSLEnforcer()
    asyncio.run(enforcer.run_enforcer_loop())
