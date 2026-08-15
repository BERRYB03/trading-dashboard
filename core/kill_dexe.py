import time
import requests
import json
import os
from auth import PionexAuth
from urllib.parse import urlencode

class SpotGridKiller:
    def __init__(self):
        self.auth = PionexAuth()
        self.base_url = "https://api.pionex.com"
        
    def kill_bot(self, buOrderId):
        endpoint = "/api/v1/bot/orders/spotGrid/cancel"
        body = {
            "buOrderId": buOrderId,
            "closeSellModel": "TO_QUOTE"
        }
        
        timestamp = int(time.time() * 1000)
        path_url = f"{endpoint}?timestamp={timestamp}"
        
        body_string = json.dumps(body, separators=(',', ':'))
        signature = self.auth.generate_signature("POST", path_url, body_string)
        
        headers = {
            "PIONEX-KEY": self.auth.api_key,
            "PIONEX-SIGNATURE": signature,
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}{path_url}"
        response = requests.post(url, headers=headers, data=body_string)
        print(f"[KILL] Response: {response.text}")

if __name__ == "__main__":
    killer = SpotGridKiller()
    killer.kill_bot("a7807e25-6ad0-469b-8fcb-f4d1771ee98b")
