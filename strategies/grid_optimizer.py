class GridOptimizer:
    def __init__(self, lower_limit: float, upper_limit: float, grid_count: int, total_investment: float):
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit
        self.grid_count = grid_count
        self.total_investment = total_investment

    def calculate_geometric_levels(self):
        """
        Calculates the price levels for a geometric grid.
        Formula: price_ratio = (upper_limit / lower_limit) ^ (1 / grid_count)
        """
        price_ratio = (self.upper_limit / self.lower_limit) ** (1.0 / self.grid_count)
        
        levels = []
        for i in range(self.grid_count + 1):
            price = self.lower_limit * (price_ratio ** i)
            levels.append(round(price, 4))
            
        return levels

    def calculate_profit_per_grid(self):
        """
        Calculates the gross percentage profit per grid execution.
        For a geometric grid, this is constant across all grids.
        """
        price_ratio = (self.upper_limit / self.lower_limit) ** (1.0 / self.grid_count)
        gross_profit_pct = (price_ratio - 1) * 100
        net_profit_pct = gross_profit_pct - 0.1  # Assuming 0.05% maker + 0.05% taker = 0.1% round-trip fee
        return round(net_profit_pct, 4)

    def calculate_capital_per_grid(self):
        """
        Distributes the capital across the grid.
        Simplified evenly distributed model.
        """
        return round(self.total_investment / self.grid_count, 4)

if __name__ == "__main__":
    # Test our exact SOL parameters
    optimizer = GridOptimizer(lower_limit=60.00, upper_limit=95.00, grid_count=18, total_investment=100.00)
    levels = optimizer.calculate_geometric_levels()
    profit = optimizer.calculate_profit_per_grid()
    cap_per_grid = optimizer.calculate_capital_per_grid()
    
    print("=== GRID OPTIMIZER METRICS ===")
    print(f"Total Grids: {optimizer.grid_count}")
    print(f"Capital Per Grid: ${cap_per_grid}")
    print(f"Net Profit Per Grid: {profit}% (Post-Fees)")
    print(f"Price Levels: {levels}")
    print("==============================")
