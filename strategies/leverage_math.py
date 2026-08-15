def analyze_leverage(entry_price, lower_limit, leverage):
    # Simplified liquidation math for a leveraged grid
    # If we are long with leverage, liquidation happens when price drops by ~ (1 / leverage)
    # Since it's a grid, we average in as it goes down.
    # At start, we buy base asset for the sell grids.
    # We will just calculate the worst-case pure long liquidation to be safe.
    max_drop = 1.0 / leverage
    liquidation_price = entry_price * (1 - max_drop)
    # Add a 5% margin of safety for maintenance margin
    safe_liquidation = liquidation_price * 1.05
    return safe_liquidation

print(f"2x Leverage Est. Liq: ${analyze_leverage(76.34, 60.00, 2):.2f}")
print(f"3x Leverage Est. Liq: ${analyze_leverage(76.34, 60.00, 3):.2f}")
print(f"4x Leverage Est. Liq: ${analyze_leverage(76.34, 60.00, 4):.2f}")
print(f"5x Leverage Est. Liq: ${analyze_leverage(76.34, 60.00, 5):.2f}")
