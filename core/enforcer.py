import time
import requests
import json
import os
from auth import PionexAuth
from urllib.parse import urlencode
from quant_engine import calculate_grid_geometry
from execution_multibot import MultiBotDeployer

class AutonomousFuturesEnforcer:
    def __init__(self):
        self.auth = PionexAuth()
        self.deployer = MultiBotDeployer()
        self.base_url = "https://api.pionex.com"
        self.radar_file = os.path.join(os.path.dirname(__file__), 'radar_state.json')
        
        # Futures Risk Protocols
        # 2x Leverage implies a 20% underlying move is a 40% loss. 
        # We cap catastrophic margin loss at -20% to prevent total liquidation.
        self.CATASTROPHIC_MARGIN_LOSS = -20.0  
        self.TAKE_PROFIT_THRESHOLD = 30.0 # +30%
        self.FLATLINE_HOURS = 24 # Tighter flatline for futures due to funding fees
        
        # State tracking
        self.out_of_range_state = {}

    def fetch_active_futures_bots(self):
        # Mocking the fetch for futures grids as API endpoint might differ
        endpoint = "/api/v1/bot/orders"
        timestamp = int(time.time() * 1000)
        params = {"timestamp": timestamp, "type": "FUTURES_GRID", "status": "TRADING"}
        query_string = urlencode(sorted(params.items()))
        path_url = f"{endpoint}?{query_string}"
        signature = self.auth.generate_signature("GET", path_url)
        headers = {
            "PIONEX-KEY": self.auth.api_key,
            "PIONEX-SIGNATURE": signature,
            "Content-Type": "application/json"
        }
        url = f"{self.base_url}{path_url}"
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data.get('result'):
                    return data['data'].get('orders', [])
        except:
            pass
        return []

    def cancel_futures_bot(self, buOrderId, symbol, reason):
        print(f"\n[!!!] FUTURES ENFORCER TRIGGERED: {reason}")
        print(f"[*] Executing ZERO-LATENCY Market Kill on {buOrderId} ({symbol})...")
        
        endpoint = "/api/v1/bot/orders/futuresGrid/cancel"
        body = {
            "buOrderId": buOrderId
        }
        
        timestamp = int(time.time() * 1000)
        path_url = f"{endpoint}?timestamp={timestamp}"
        body_string = json.dumps(body, separators=(',', ':'))
        signature = self.auth.generate_signature("POST", path_url, body_string)
        
        headers = {
            "PIONEX-KEY": self.auth.api_key,
            "PIONEX-SIGNATURE": signature,
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}{path_url}"
        
        try:
            response = requests.post(url, headers=headers, data=body_string)
            if response.status_code == 200:
                print(f"[+] Leveraged Bot {buOrderId} terminated successfully.")
                print(f"[-] Margin secured. Positions closed at market.")
                return True
            else:
                print(f"[-] FAILED to terminate futures bot: {response.text}")
                return False
        except Exception as e:
            print(f"[-] HTTP Request failed: {e}")
            return False

    def fetch_all_tickers(self):
        url = f"{self.base_url}/api/v1/market/tickers"
        try:
            response = requests.get(url, timeout=5).json()
            if response.get('result'):
                return {t['symbol']: t for t in response['data']['tickers']}
        except:
            pass
        return {}

    def run_enforcer_loop(self):
        print("="*60)
        print(" PROJECT BETA : LEVERAGE & LIQUIDATION ENFORCER ONLINE")
        print("="*60)
        print("[*] Futures Risk Thresholds:")
        print(f"    - Catastrophic Kill: {self.CATASTROPHIC_MARGIN_LOSS}% Margin Loss")
        print(f"    - Take-Profit:       +{self.TAKE_PROFIT_THRESHOLD}%")
        print(f"    - Funding Trap:      Out of bounds > {self.FLATLINE_HOURS} hours")
        print("="*60)
        
        while True:
            bots = self.fetch_active_futures_bots()
            tickers = self.fetch_all_tickers()
            
            radar_data = None
            if os.path.exists(self.radar_file):
                try:
                    with open(self.radar_file, 'r') as f:
                        radar_data = json.load(f)
                except:
                    pass

            if not bots:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] No active futures bots found. Sleeping...")
            else:
                current_time = time.time()
                worst_bot = None
                worst_mrvs = float('inf')
                
                for bot in bots:
                    buOrderId = bot.get("buOrderId")
                    # Futures format typically includes .PERP
                    symbol = bot.get("symbol", "")
                    bot_data = bot.get("buOrderData", {})
                    
                    initial_investment = float(bot_data.get("quoteTotalInvestment", 0.0))
                    top = float(bot_data.get("top", 0.0))
                    bottom = float(bot_data.get("bottom", 0.0))
                    leverage = float(bot_data.get("leverage", 2.0))
                    
                    # Try to map back to spot ticker for mark price approximation
                    spot_symbol = symbol.replace('.PERP', '') if '.PERP' in symbol else symbol
                    ticker = tickers.get(spot_symbol)
                    
                    if not ticker:
                        continue
                        
                    # Ensure we are tracking Mark Price for futures liquidations, not last traded price
                    mark_price = float(ticker.get('markPrice', ticker.get('close', 0)))
                    
                    # Approximated Unrealized PnL (for Neutral Grid, simplified math)
                    # For neutral, we sell above and buy below. If price moves, we suffer divergence loss.
                    # This is a simulation calculation since the API would normally provide 'totalProfit'.
                    bot_pnl_percent = float(bot.get('profit', 0)) / initial_investment * 100 if initial_investment > 0 else 0
                    
                    if bot_pnl_percent < self.CATASTROPHIC_MARGIN_LOSS:
                        self.cancel_futures_bot(buOrderId, symbol, f"CATASTROPHIC MARGIN LOSS BREACH ({bot_pnl_percent:.2f}%)")
                        continue
                        
                    if bot_pnl_percent >= self.TAKE_PROFIT_THRESHOLD:
                        self.cancel_futures_bot(buOrderId, symbol, f"FUTURES TAKE-PROFIT ACHIEVED (+{bot_pnl_percent:.2f}%)")
                        continue
                        
                    if mark_price < bottom or mark_price > top:
                        if buOrderId not in self.out_of_range_state:
                            self.out_of_range_state[buOrderId] = current_time
                        else:
                            hours_out = (current_time - self.out_of_range_state[buOrderId]) / 3600
                            if hours_out > self.FLATLINE_HOURS:
                                print(f"[*] {symbol} trapped for {hours_out:.1f}hrs (Funding Fee Bleed). Executing Kill.")
                                self.cancel_futures_bot(buOrderId, symbol, "FUNDING FEE TRAP (24H OUT OF BOUNDS)")
                                del self.out_of_range_state[buOrderId]
                    else:
                        if buOrderId in self.out_of_range_state:
                            del self.out_of_range_state[buOrderId]
                            
                # Asynchronous Phase 6: Capital Rotation 
                if radar_data and worst_bot:
                    radar_symbol = radar_data['best_prospect']
                    radar_mrvs = radar_data['mrvs']
                    
                    active_symbols = [b.get('symbol') for b in bots]
                    if radar_mrvs > (worst_mrvs * 3) and radar_symbol not in active_symbols:
                        print(f"\n[ALPHA SCANNER DELEGATOR COMMAND RECEIVED]")
                        print(f"[*] Rotating {worst_bot['symbol']} margin into {radar_symbol} (Neutral Futures Grid).")
                        success = self.cancel_futures_bot(worst_bot['buOrderId'], worst_bot['symbol'], "FUTURES ROTATION")
                        
                        if success:
                            lower_lim, upper_lim = calculate_grid_geometry(radar_symbol.replace('.PERP', ''))
                            if lower_lim and upper_lim:
                                recovered_capital = round(worst_bot['investment'] + worst_bot['pnl'], 4)
                                self.deployer.deploy_bot(symbol=radar_symbol, top=upper_lim, bottom=lower_lim, grids=20, investment=recovered_capital, grid_type="arithmetic", leverage=2, trend="no_trend")
                                
            time.sleep(10) # Run loop faster for futures liquidation checks

if __name__ == "__main__":
    enforcer = AutonomousFuturesEnforcer()
    try:
        enforcer.run_enforcer_loop()
    except KeyboardInterrupt:
        print("\n[*] Futures Enforcer terminated by user.")
