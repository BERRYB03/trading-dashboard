import os
import time
import json
import requests
import asyncio
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env')
load_dotenv(env_path)

class DualArchitectureScanner:
    def __init__(self):
        self.base_url = "https://api.pionex.com"
        self.radar_file = os.path.join(os.path.dirname(__file__), 'radar_state.json')
        self.gamma_radar_file = os.path.join(os.path.dirname(__file__), 'gamma_radar_state.json')
        self.ledger_file = os.path.join(os.path.dirname(__file__), 'failures_ledger.json')
        
        self.min_volume_usdt = 5000000  # $5M 24h volume minimum
        self.BETA_RESERVE = 55.00
        self.GAMMA_RESERVE = 38.87

    def fetch_tickers(self):
        url = f"{self.base_url}/api/v1/market/tickers"
        try:
            response = requests.get(url, timeout=5).json()
            if response.get('result'):
                return response['data']['tickers']
        except Exception as e:
            print(f"[-] Scanner failed to fetch tickers: {e}")
        return []

    def calculate_mrvs(self, ticker):
        try:
            high = float(ticker['high'])
            low = float(ticker['low'])
            open_p = float(ticker['open'])
            close = float(ticker['close'])
            if close == 0 or high == low or open_p == 0: return 0
            v = (high - low) / close
            d = abs(close - open_p) / (high - low)
            return v * (1 - d)
        except:
            return 0

    def check_historical_failures(self, symbol, daily_change, volume):
        if not os.path.exists(self.ledger_file):
            return None
            
        try:
            with open(self.ledger_file, 'r') as f:
                ledger = json.load(f)
                
            for autopsy in ledger:
                # Check for same asset OR similar conditions (within 20% variance on change and volume)
                past_change = autopsy['entry_conditions']['daily_change']
                past_vol = autopsy['entry_conditions']['volume']
                
                if past_change == 0 or past_vol == 0: continue
                
                change_variance = abs(daily_change - past_change) / abs(past_change)
                vol_variance = abs(volume - past_vol) / abs(past_vol)
                
                if (symbol == autopsy['symbol'].replace('.PERP', '')) or (change_variance <= 0.20 and vol_variance <= 0.20):
                    return autopsy
        except Exception as e:
            print(f"[-] RAG Ledger Read Error: {e}")
        return None

    async def _delegate_beta_sentiment(self, symbol, mrvs, amount, price):
        pass # Beta execution remains stateless for now

    async def _delegate_gamma_sentiment(self, symbol, daily_change, amount, price):
        print(f"[!!!] Dispatching GAMMA Strategist for {symbol} (Parabolic Pump: +{daily_change:.2f}%)...")
        try:
            from core.sentiment_engine import SentimentAnalyzer
            analyzer = SentimentAnalyzer()
            
            context = {
                "symbol": symbol, 
                "event": "GAMMA_PARABOLIC_BREAKOUT", 
                "24h_change": daily_change, 
                "volume": amount,
                "price": price
            }
            
            # MEMORY RETRIEVAL (Context Injection)
            historical_match = self.check_historical_failures(symbol, daily_change, amount)
            if historical_match:
                print(f"[*] RAG SYSTEM: Historical failure match detected for {symbol}. Injecting Warning Context.")
                context['historical_warning'] = {
                    "direction": historical_match['original_direction'],
                    "failure_reason": historical_match['failure_trigger']
                }
            
            sentiment = await asyncio.to_thread(analyzer.analyze_event, context)
            
            decision = sentiment.get('decision')
            confidence = sentiment.get('confidence', 0)
            direction = sentiment.get('direction', 'neutral')
            
            if decision == 'EXECUTE' and confidence >= 90:
                state = {
                    'timestamp': time.time(), 'target': symbol, 'direction': direction, 
                    'price': price, 'allocation': self.GAMMA_RESERVE, 'engine': 'GAMMA',
                    'daily_change': daily_change, 'volume': amount, 'confidence': confidence
                }
                with open(self.gamma_radar_file, 'w') as f: json.dump(state, f, indent=4)
                print(f"[+] GAMMA SNIPER AUTHORIZED: {symbol} | Dir: {direction.upper()} | Conf: {confidence}")
            else:
                print(f"[-] GAMMA Rejected {symbol}. Confidence too low ({confidence}).")
        except Exception as e:
            print(f"[-] GAMMA Swarm failed: {e}")

    async def run_scan(self):
        print(f"[{time.strftime('%H:%M:%S')}] Dual Scanner + RAG Loop Initiating Reconnaissance...")
        tickers = await asyncio.to_thread(self.fetch_tickers)
        
        for t in tickers:
            symbol = t.get('symbol', '')
            if not symbol.endswith('_USDT'): continue
            if 'UP_' in symbol or 'DOWN_' in symbol: continue
                
            amount = float(t.get('amount', 0))
            if amount < self.min_volume_usdt: continue
                
            close = float(t.get('close', 0))
            open_p = float(t.get('open', 0))
            high = float(t.get('high', 0))
            if open_p == 0 or high == 0: continue
            
            daily_change = ((close - open_p) / open_p) * 100
            
            if daily_change > 15.0:
                if amount > self.min_volume_usdt * 3:
                    asyncio.create_task(self._delegate_gamma_sentiment(symbol, daily_change, amount, close))
                continue

    async def start(self):
        print("============================================================")
        print(" PROJECT GAMMA : RAG POST-MORTEM SCANNER ONLINE")
        print("============================================================")
        while True:
            await self.run_scan()
            await asyncio.sleep(60)

if __name__ == "__main__":
    scanner = DualArchitectureScanner()
    try:
        asyncio.run(scanner.start())
    except KeyboardInterrupt:
        print("\n[*] Scanner terminated.")
