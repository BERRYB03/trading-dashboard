import time
import hmac
import hashlib
import requests
import json
import os
from dotenv import load_dotenv
from core.gcp_secrets import get_secret

# Load local environment vars as a fallback for GCP_PROJECT_ID if running locally
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env')
load_dotenv(env_path)

class PionexAuth:
    def __init__(self):
        # Dynamically fetch from GCP Secret Manager (falls back to local env if running outside GCP)
        self.api_key = get_secret('PIONEX_API_KEY')
        self.api_secret = get_secret('PIONEX_API_SECRET')
        self.base_url = "https://api.pionex.com"

        if not self.api_key or not self.api_secret or self.api_key == 'YOUR_API_KEY_HERE':
            raise ValueError("CRITICAL ERROR: PIONEX_API_KEY or SECRET is missing from Secret Manager.")

    def generate_signature(self, method, path_url, body_string=""):
        message = f"{method}{path_url}{body_string}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def fetch_balances(self):
        endpoint = "/api/v1/account/balances"
        timestamp = int(time.time() * 1000)
        path_url = f"{endpoint}?timestamp={timestamp}"
        
        signature = self.generate_signature("GET", path_url)
        
        headers = {
            "PIONEX-KEY": self.api_key,
            "PIONEX-SIGNATURE": signature,
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}{path_url}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data.get('result'):
                return data.get('data')
            else:
                return None
        except Exception as e:
            return None

if __name__ == "__main__":
    print("[SYSTEM] Initializing GCP Authentication Protocol...")
    auth = PionexAuth()
    print("[SYSTEM] Authentication successful. Fetching balances...")
    balances = auth.fetch_balances()
    if balances:
        print("\n=== LIVE ACCOUNT BALANCES ===")
        for item in balances.get('balances', []):
            free_amt = float(item.get('free', 0))
            locked_amt = float(item.get('locked', 0))
            if free_amt > 0 or locked_amt > 0:
                 print(f"Asset: {item.get('coin', 'UNKNOWN')} | Free: {free_amt} | Locked: {locked_amt}")
        print("=============================\n")
    else:
        print("[ERROR] Failed to fetch balances. Check your credentials or rate limits.")
