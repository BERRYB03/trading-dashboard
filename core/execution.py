import os
import time
import hmac
import hashlib
import json
import requests
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env')
load_dotenv(env_path)

class PionexDeployer:
    def __init__(self):
        self.api_key = os.getenv('PIONEX_API_KEY')
        self.api_secret = os.getenv('PIONEX_API_SECRET')
        self.base_url = "https://api.pionex.com"
        
        if not self.api_key or not self.api_secret:
            raise ValueError("[CRITICAL ERROR] API Keys missing in .env")

    def generate_signature(self, method, path_url, body_string=""):
        """Generates HMAC SHA256 Signature for Pionex"""
        message = f"{method}{path_url}{body_string}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def deploy_leveraged_grid(self):
        """Deploys a 2x Leveraged Futures Grid Bot on SOL_USDT_PERP"""
        endpoint = "/api/v1/bot/orders/futuresGrid/create"
        timestamp = int(time.time() * 1000)
        
        # Mathematical Parameters Authorized:
        # 100 USDT Margin, 2x Leverage
        # SOL/USDT Geometric Grid: 18 Grids between $60.00 and $95.00
        payload = {
            "symbol": "SOL_USDT_PERP", # Futures market required for Leverage
            "botType": "FUTURES_GRID",
            "botParams": {
                "gridType": "geometric",
                "leverage": 2,
                "top": "95.00",
                "bottom": "60.00",
                "row": 18,
                "margin": "100.00" 
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
        print(f"[SYSTEM] Initiating LIVE DEPLOYMENT: 2x Leveraged Grid on SOL_USDT_PERP...")
        print(f"[SYSTEM] Capital Allocated: 100 USDT | Operating Capital: 200 USDT")
        print(f"[SYSTEM] Range: $60.00 - $95.00 | Grid Count: 18 Geometric")
        
        # WARNING: Uncommenting the next lines will execute real trades on the exchange.
        # response = requests.post(url, headers=headers, data=body_string)
        # 
        # if response.status_code == 200:
        #     print("[SUCCESS] Bot successfully deployed to Pionex.")
        #     return response.json()
        # else:
        #     print(f"[CRITICAL ERROR] Deployment Failed: {response.status_code}")
        #     print(response.text)
        #     return None

        print("[SYSTEM] Deployment script staged. Waiting for user funding and final 'go' command to uncomment the POST request.")

if __name__ == "__main__":
    deployer = PionexDeployer()
    deployer.deploy_leveraged_grid()
