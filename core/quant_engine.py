import requests
import numpy as np

def calculate_grid_geometry(symbol):
    """Calculates optimal BB and ATR based grid boundaries."""
    url = f"https://api.pionex.com/api/v1/market/klines?symbol={symbol}&interval=60M&limit=100"
    try:
        response = requests.get(url).json()
    except Exception as e:
        print(f"[-] Network error calculating grid: {e}")
        return None, None
        
    if not response.get('result'):
        return None, None
        
    klines = response['data']['klines']
    closes = np.array([float(k['close']) for k in klines])
    highs = np.array([float(k['high']) for k in klines])
    lows = np.array([float(k['low']) for k in klines])
    
    # 20-period SMA for BB
    sma_20 = np.mean(closes[-20:])
    std_20 = np.std(closes[-20:])
    upper_bb = sma_20 + (2 * std_20)
    lower_bb = sma_20 - (2 * std_20)
    
    # 14-period ATR
    tr_list = []
    for i in range(1, 15):
        idx = -i
        h, l, pc = highs[idx], lows[idx], closes[idx-1]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        tr_list.append(tr)
    atr_14 = np.mean(tr_list)
    
    lower_limit = lower_bb - atr_14
    upper_limit = upper_bb + atr_14
    
    # Find decimal precision of current price to round appropriately
    price_str = klines[-1]['close']
    precision = 4
    if '.' in price_str:
        precision = len(price_str.split('.')[1])
        
    return round(lower_limit, precision), round(upper_limit, precision)
