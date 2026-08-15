import requests
import json

def scan_market():
    print("[SCANNER] Fetching live market data across all Pionex pairs...")
    base_url = "https://api.pionex.com"
    endpoint = "/api/v1/market/tickers"
    
    response = requests.get(base_url + endpoint)
    if response.status_code != 200:
        print(f"Error fetching data: {response.status_code}")
        return
        
    data = response.json()
    if not data.get('result'):
        print("API Error")
        return
        
    tickers = data['data']['tickers']
    
    # Filter for USDT pairs with decent volume (e.g., > 1,000,000 USDT in 24h)
    # We want to avoid dead, low-liquidity coins.
    valid_pairs = []
    for t in tickers:
        if t['symbol'].endswith('_USDT'):
            try:
                volume_usdt = float(t['amount'])
                if volume_usdt > 1000000: # $1M daily volume
                    high = float(t['high'])
                    low = float(t['low'])
                    if low > 0:
                        volatility = ((high - low) / low) * 100 # 24h volatility %
                        t['volatility'] = volatility
                        valid_pairs.append(t)
            except (ValueError, KeyError, TypeError):
                continue
                
    # Rank by volatility descending
    valid_pairs.sort(key=lambda x: x['volatility'], reverse=True)
    
    print("\n=== TOP 10 HIGH-VOLATILITY, HIGH-LIQUIDITY PAIRS (24H) ===")
    for i, t in enumerate(valid_pairs[:10]):
        print(f"{i+1}. {t['symbol']} | Price: ${float(t['close']):.4f} | Volatility: {t['volatility']:.2f}% | Vol: ${float(t['amount']):,.0f}")

    # Specific check on majors
    print("\n=== MAJORS CHECK ===")
    majors = [t for t in valid_pairs if t['symbol'] in ['BTC_USDT', 'ETH_USDT', 'SOL_USDT']]
    for t in majors:
        print(f"{t['symbol']} | Price: ${float(t['close']):.4f} | Volatility: {t['volatility']:.2f}% | Vol: ${float(t['amount']):,.0f}")


if __name__ == "__main__":
    scan_market()
