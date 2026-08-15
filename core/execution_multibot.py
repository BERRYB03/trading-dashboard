import os
import time
import hmac
import hashlib
import json
import requests
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env')
load_dotenv(env_path)

class MultiBotDeployer:
    def __init__(self):
        self.api_key = os.getenv('PIONEX_API_KEY')
        self.api_secret = os.getenv('PIONEX_API_SECRET')
        self.base_url = "https://api.pionex.com"
        
        if not self.api_key or not self.api_secret:
            raise ValueError("[CRITICAL ERROR] API Keys missing in .env")

    def generate_signature(self, method, path_url, body_string=""):
        message = f"{method}{path_url}{body_string}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def deploy_bot(self, symbol, top, bottom, grids, investment, grid_type="arithmetic", leverage=2, trend="no_trend"):
        endpoint = "/api/v1/bot/orders/futuresGrid/create"
        timestamp = int(time.time() * 1000)
        
        # In futures, the symbol is usually BASE_QUOTE.PERP or similar. We will just use what is passed.
        # Ensure it ends with .PERP if the system expects it, but we can pass symbol directly.
        if not symbol.endswith(".PERP"):
             symbol += ".PERP"
             
        payload = {
            "symbol": symbol,
            "buOrderData": {
                "gridType": grid_type,
                "top": str(top),
                "bottom": str(bottom),
                "row": grids,
                "quoteTotalInvestment": str(investment),
                "leverage": leverage,
                "trend": "no_trend"
            }
        }
        
        path_url = f"{endpoint}?timestamp={timestamp}"
        body_string = json.dumps(payload, separators=(',', ':'))
        signature = self.generate_signature("POST", path_url, body_string)
        
        headers = {
            "PIONEX-KEY": self.api_key,
            "PIONEX-SIGNATURE": signature,
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}{path_url}"
        print(f"[SYSTEM] Staged Deployment: {symbol} Futures Grid ({trend})")
        print(f"         Investment: {investment} USDT | Range: {bottom} - {top} ({grids} Grids) | Leverage: {leverage}x")
        
        response = requests.post(url, headers=headers, data=body_string)
        if response.status_code == 200:
            print(f"[SUCCESS] Bot deployed successfully: {response.json()}")
        else:
            print(f"[ERROR] Failed to deploy {symbol}: {response.text}")
        
    def execute_fleet(self):
        print("=== INITIATING PROJECT BETA DEPLOYMENT ===")
        # Testing a neutral futures grid
        self.deploy_bot(symbol="BTC_USDT.PERP", top=65000, bottom=55000, grids=20, investment=20, grid_type="arithmetic", leverage=2, trend="no_trend")

if __name__ == "__main__":
    deployer = MultiBotDeployer()
    deployer.execute_fleet()
