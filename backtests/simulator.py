import os
import sys
import json
import requests
import time

# Add parent directory to path to import strategies
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strategies.grid_optimizer import GridOptimizer

class GridSimulator:
    def __init__(self, symbol: str, optimizer: GridOptimizer):
        self.symbol = symbol
        self.optimizer = optimizer
        self.base_url = "https://api.pionex.com"
        self.klines = []
        
    def fetch_data(self):
        """Fetches the last 500 hours (~20.8 days) of Kline data."""
        print(f"[SIMULATOR] Fetching Historical Data for {self.symbol}...")
        endpoint = f"/api/v1/market/klines?symbol={self.symbol}&interval=60M&limit=500"
        response = requests.get(self.base_url + endpoint)
        
        if response.status_code == 200:
            data = response.json()
            if data['result']:
                self.klines = data['data']['klines']
                print(f"[SIMULATOR] Successfully loaded {len(self.klines)} hourly candles.")
            else:
                print(f"[SIMULATOR] Error from API: {data['message']}")
        else:
            print(f"[SIMULATOR] HTTP Error: {response.status_code}")

    def run_simulation(self):
        if not self.klines:
            print("[SIMULATOR] No data to simulate.")
            return

        levels = self.optimizer.calculate_geometric_levels()
        cap_per_grid = self.optimizer.calculate_capital_per_grid()
        
        # Sort levels to be sure
        levels = sorted(levels)
        
        # Initial parameters
        initial_price = float(self.klines[-1]['close']) # Pionex klines are newest first? Let's check.
        # Actually Pionex klines usually have the oldest first or newest first. Let's assume standard oldest first.
        # Wait, if I fetched 500 limit, the 0th index is the oldest.
        initial_price = float(self.klines[-1]['close']) 
        
        # Let's verify chronological order by checking timestamps
        if self.klines[0]['time'] > self.klines[-1]['time']:
            self.klines.reverse() # ensure oldest first
            
        initial_price = float(self.klines[0]['open'])
        print(f"[SIMULATOR] Starting Price: ${initial_price:.2f}")

        # Distribute Initial Capital
        buy_grids = [lvl for lvl in levels if lvl < initial_price]
        sell_grids = [lvl for lvl in levels if lvl >= initial_price]
        
        # We need to buy base currency for the sell grids at the initial_price
        base_asset = 0.0
        quote_asset = self.optimizer.total_investment
        
        required_quote_for_base = len(sell_grids) * cap_per_grid
        
        if quote_asset < required_quote_for_base:
            print("[SIMULATOR] Warning: Not enough capital to place all sell grids initially.")
            required_quote_for_base = quote_asset
            
        quote_asset -= required_quote_for_base
        base_asset += (required_quote_for_base / initial_price) * 0.999 # accounting for 0.1% fee
        
        print(f"[SIMULATOR] Initial Buy-In: Bought {base_asset:.4f} base asset with ${required_quote_for_base:.2f}")
        
        trades = 0
        grid_profit = 0.0
        
        current_active_sell = sell_grids.copy()
        current_active_buy = buy_grids.copy()
        current_active_sell.sort()
        current_active_buy.sort(reverse=True) # highest buy grids first

        for kline in self.klines:
            low = float(kline['low'])
            high = float(kline['high'])
            
            # Check for buys (price goes down)
            buys_to_remove = []
            for buy_price in current_active_buy:
                if low <= buy_price:
                    # Execute Buy
                    if quote_asset >= cap_per_grid:
                        quote_asset -= cap_per_grid
                        base_asset += (cap_per_grid / buy_price) * 0.9995 # 0.05% fee
                        trades += 1
                        # This buy grid now becomes a sell grid at the next level up
                        idx = levels.index(buy_price)
                        if idx + 1 < len(levels):
                            current_active_sell.append(levels[idx + 1])
                            current_active_sell.sort()
                        buys_to_remove.append(buy_price)
            for b in buys_to_remove:
                current_active_buy.remove(b)
                
            # Check for sells (price goes up)
            sells_to_remove = []
            for sell_price in current_active_sell:
                if high >= sell_price:
                    # Execute Sell
                    sell_amount_base = (cap_per_grid / sell_price) # sell equivalent of cap_per_grid
                    if base_asset >= sell_amount_base:
                        base_asset -= sell_amount_base
                        proceeds = sell_amount_base * sell_price * 0.9995 # 0.05% fee
                        quote_asset += proceeds
                        trades += 1
                        
                        # Calculate profit realized
                        # The buy price was the previous grid level
                        idx = levels.index(sell_price)
                        if idx - 1 >= 0:
                            buy_price = levels[idx - 1]
                            profit = (sell_amount_base * sell_price * 0.9995) - (sell_amount_base * buy_price / 0.9995)
                            grid_profit += profit

                        # This sell grid now becomes a buy grid at the next level down
                        if idx - 1 >= 0:
                            current_active_buy.append(levels[idx - 1])
                            current_active_buy.sort(reverse=True)
                        sells_to_remove.append(sell_price)
            for s in sells_to_remove:
                current_active_sell.remove(s)

        final_price = float(self.klines[-1]['close'])
        final_portfolio_value = quote_asset + (base_asset * final_price)
        total_roi = ((final_portfolio_value / self.optimizer.total_investment) - 1) * 100

        print("\n=== BACKTEST RESULTS (Last ~20 Days) ===")
        print(f"Final Price: ${final_price:.2f}")
        print(f"Total Grid Executions (Buy/Sell): {trades}")
        print(f"Grid Profit Extracted: ${grid_profit:.2f}")
        print(f"Final Portfolio Value: ${final_portfolio_value:.2f}")
        print(f"Total ROI: {total_roi:.2f}%")
        print("=========================================\n")

if __name__ == "__main__":
    optimizer = GridOptimizer(lower_limit=60.00, upper_limit=95.00, grid_count=18, total_investment=100.00)
    sim = GridSimulator(symbol="SOL_USDT", optimizer=optimizer)
    sim.fetch_data()
    sim.run_simulation()
