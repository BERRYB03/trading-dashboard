import requests
import json
import time
from urllib.parse import urlencode
from auth import PionexAuth

class BotMonitor:
    def __init__(self):
        self.auth = PionexAuth()
        self.base_url = "https://api.pionex.com"
        
    def fetch_active_bots(self):
        """Fetches all running spot grid bots."""
        endpoint = "/api/v1/bot/orders"
        params = {
            "status": "running"
        }
        
        timestamp = int(time.time() * 1000)
        params["timestamp"] = timestamp
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
            if response.status_code != 200:
                print(f"[-] Failed to fetch bots: {response.status_code}")
                print(response.text)
                return []
                
            data = response.json()
            if data.get("result"):
                return data.get("data", {}).get("results", [])
        except Exception as e:
            print(f"[-] Network error fetching bots: {e}")
        return []
        
    def fetch_market_price(self, symbol):
        """Fetches the current market price for a given pair."""
        endpoint = "/api/v1/market/tickers"
        params = {"symbol": symbol}
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get("result") and data.get("data", {}).get("tickers"):
                    return float(data["data"]["tickers"][0]["close"])
        except Exception as e:
            print(f"[-] Network error fetching price for {symbol}: {e}")
        return 0.0

    def print_dashboard(self):
        print("="*60)
        print(" PROJECT ALPHA : TELEMETRY PIPELINE")
        print("="*60)
        
        bots = self.fetch_active_bots()
        if not bots:
            print("[-] No active bots detected.")
            return

        total_investment = 0.0
        total_pnl = 0.0

        for bot in bots:
            base = bot.get("base")
            quote = bot.get("quote")
            symbol = f"{base}_{quote}"
            bot_data = bot.get("buOrderData", {})
            
            # Extract raw string values and cast to float
            initial_investment = float(bot_data.get("quoteTotalInvestment", 0.0))
            base_amount = float(bot_data.get("baseAmount", 0.0))
            quote_amount = float(bot_data.get("quoteAmount", 0.0))
            grid_profit = float(bot_data.get("gridProfit", 0.0))
            
            # Fetch live price
            current_price = self.fetch_market_price(symbol)
            if current_price == 0.0:
                print(f"[-] Failed to fetch live price for {symbol}")
                continue
                
            # Calculate metrics
            base_value_in_quote = base_amount * current_price
            current_total_value = base_value_in_quote + quote_amount
            
            # The exact definition of total PnL includes the current equity vs initial investment.
            bot_total_pnl = current_total_value - initial_investment
            bot_pnl_percent = (bot_total_pnl / initial_investment) * 100 if initial_investment > 0 else 0
            
            total_investment += initial_investment
            total_pnl += bot_total_pnl
            
            # Output formatting
            status_color = "\033[92m" if bot_pnl_percent >= 0 else "\033[91m"
            reset_color = "\033[0m"
            
            print(f" {status_color}* TARGET: {symbol}{reset_color}")
            print(f"   - Live Price:     {current_price} {quote}")
            print(f"   - Capital Seed:   {initial_investment:.2f} {quote}")
            print(f"   - Current Value:  {current_total_value:.2f} {quote}")
            print(f"   - Base Held:      {base_amount:.4f} {base}")
            print(f"   - Quote Held:     {quote_amount:.4f} {quote}")
            print(f"   - Grid Profit:    {grid_profit:.4f} {quote}")
            print(f"   - Total PnL:      {status_color}{bot_total_pnl:+.4f} {quote} ({bot_pnl_percent:+.2f}%){reset_color}")
            print("-" * 60)

        print(f" [TOTAL FLEET EXPOSURE]  : {total_investment:.2f} USDT")
        fleet_color = "\033[92m" if total_pnl >= 0 else "\033[91m"
        fleet_pnl_percent = (total_pnl / total_investment) * 100 if total_investment > 0 else 0
        print(f" [FLEET TOTAL PNL]       : {fleet_color}{total_pnl:+.4f} USDT ({fleet_pnl_percent:+.2f}%)\033[0m")
        print("="*60)


if __name__ == "__main__":
    monitor = BotMonitor()
    monitor.print_dashboard()
