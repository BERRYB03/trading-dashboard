import os
import sys
import json
import requests
import time

# Add parent directory to path to import strategies
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strategies.grid_optimizer import GridOptimizer

class GridSimulatorExtended:
    def __init__(self, symbol: str, optimizer: GridOptimizer, leverage: float = 1.0):
        self.symbol = symbol
        self.optimizer = optimizer
        self.leverage = leverage
        self.base_url = "https://api.pionex.com"
        self.klines = []
        
        # Calculate Leveraged Investment
        self.seed_capital = self.optimizer.total_investment
        self.borrowed_capital = self.seed_capital * (self.leverage - 1)
        self.active_capital = self.seed_capital + self.borrowed_capital
        
        # Daily interest rate on borrowed funds (Conservative estimate: 0.1% daily)
        self.daily_interest_rate = 0.001 
        
    def fetch_deep_data(self, target_candles: int = 2000):
        print(f"[SIMULATOR] Fetching Deep Historical Data for {self.symbol}...")
        all_klines = []
        end_time = None
        
        while len(all_klines) < target_candles:
            endpoint = f"/api/v1/market/klines?symbol={self.symbol}&interval=60M&limit=500"
            if end_time:
                endpoint += f"&endTime={end_time}"
                
            response = requests.get(self.base_url + endpoint)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('result') and data['data'].get('klines'):
                    chunk = data['data']['klines']
                    if not chunk: break 
                    all_klines = chunk + all_klines
                    end_time = int(chunk[0]['time']) - 1
                    time.sleep(0.2) 
                else:
                    break
            else:
                break
                
        self.klines = all_klines
        print(f"[SIMULATOR] Successfully loaded {len(self.klines)} hourly candles.")

    def run_simulation(self):
        if not self.klines: return

        # Override optimizer total_investment with our leveraged active_capital for grid calculations
        original_investment = self.optimizer.total_investment
        self.optimizer.total_investment = self.active_capital
        
        levels = self.optimizer.calculate_geometric_levels()
        cap_per_grid = self.optimizer.calculate_capital_per_grid()
        levels = sorted(levels)
        
        if self.klines[0]['time'] > self.klines[-1]['time']:
            self.klines.reverse()
            
        initial_price = float(self.klines[0]['open'])
        print(f"[SIMULATOR] Starting Price: ${initial_price:.2f} with {self.leverage}x Leverage")

        buy_grids = [lvl for lvl in levels if lvl < initial_price]
        sell_grids = [lvl for lvl in levels if lvl >= initial_price]
        
        base_asset = 0.0
        quote_asset = self.active_capital
        
        required_quote_for_base = len(sell_grids) * cap_per_grid
        
        if quote_asset < required_quote_for_base:
            required_quote_for_base = quote_asset
            
        quote_asset -= required_quote_for_base
        base_asset += (required_quote_for_base / initial_price) * 0.999 
        
        trades = 0
        grid_profit = 0.0
        
        current_active_sell = sell_grids.copy()
        current_active_buy = buy_grids.copy()
        current_active_sell.sort()
        current_active_buy.sort(reverse=True)

        for kline in self.klines:
            low = float(kline['low'])
            high = float(kline['high'])
            
            buys_to_remove = []
            for buy_price in current_active_buy:
                if low <= buy_price:
                    if quote_asset >= cap_per_grid:
                        quote_asset -= cap_per_grid
                        base_asset += (cap_per_grid / buy_price) * 0.9995 
                        trades += 1
                        idx = levels.index(buy_price)
                        if idx + 1 < len(levels):
                            current_active_sell.append(levels[idx + 1])
                            current_active_sell.sort()
                        buys_to_remove.append(buy_price)
            for b in buys_to_remove: current_active_buy.remove(b)
                
            sells_to_remove = []
            for sell_price in current_active_sell:
                if high >= sell_price:
                    sell_amount_base = (cap_per_grid / sell_price)
                    if base_asset >= sell_amount_base:
                        base_asset -= sell_amount_base
                        quote_asset += sell_amount_base * sell_price * 0.9995
                        trades += 1
                        
                        idx = levels.index(sell_price)
                        if idx - 1 >= 0:
                            buy_price = levels[idx - 1]
                            profit = (sell_amount_base * sell_price * 0.9995) - (sell_amount_base * buy_price / 0.9995)
                            grid_profit += profit

                        if idx - 1 >= 0:
                            current_active_buy.append(levels[idx - 1])
                            current_active_buy.sort(reverse=True)
                        sells_to_remove.append(sell_price)
            for s in sells_to_remove: current_active_sell.remove(s)

        # Calculate Funding Costs
        total_hours = len(self.klines)
        total_days = total_hours / 24.0
        total_interest = total_days * self.daily_interest_rate * self.borrowed_capital

        final_price = float(self.klines[-1]['close'])
        
        # Portfolio value is total assets minus borrowed capital minus interest paid
        final_portfolio_value = quote_asset + (base_asset * final_price)
        net_equity = final_portfolio_value - self.borrowed_capital - total_interest
        
        total_roi = ((net_equity / self.seed_capital) - 1) * 100
        buy_and_hold_roi = ((final_price / initial_price) - 1) * 100

        print("\n=== DEEP LEVERAGE BACKTEST RESULTS ===")
        print(f"Leverage Profile: {self.leverage}x | Seed Capital: ${self.seed_capital:.2f} | Borrowed: ${self.borrowed_capital:.2f}")
        print(f"Days Simulated: {total_days:.1f} Days")
        print(f"Starting Price: ${initial_price:.2f} | Final Price: ${final_price:.2f}")
        print(f"Buy & Hold ROI: {buy_and_hold_roi:.2f}%")
        print(f"Total Grid Executions: {trades}")
        print(f"Gross Grid Profit: ${grid_profit:.2f}")
        print(f"Total Margin Interest Paid: -${total_interest:.2f}")
        print(f"Final Net Equity: ${net_equity:.2f}")
        print(f"Grid Strategy Net ROI: {total_roi:.2f}%")
        print("======================================\n")

if __name__ == "__main__":
    optimizer = GridOptimizer(lower_limit=60.00, upper_limit=95.00, grid_count=18, total_investment=100.00)
    # Using the strictly authorized 2x Leverage
    sim = GridSimulatorExtended(symbol="SOL_USDT", optimizer=optimizer, leverage=2.0)
    sim.fetch_deep_data(target_candles=2500)
    sim.run_simulation()
