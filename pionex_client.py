"""
Pionex execution and market-data client.

Implements HMAC-SHA256 authenticated endpoints for LIVE execution,
and public endpoints for order book telemetry.
"""

import time
import requests
import hmac
import hashlib
import json
from urllib.parse import urlencode

BASE_URL = "https://api.pionex.com"

class PionexAPIError(Exception):
    pass

class PionexClient:
    def __init__(self, api_key=None, api_secret=None, timeout=5, max_retries=3):
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()

    def _generate_signature(self, method, path, params=None, body=None):
        timestamp = int(time.time() * 1000)
        p = params.copy() if params else {}
        p['timestamp'] = timestamp
        
        sorted_params = sorted(p.items())
        query_string = urlencode(sorted_params)
        
        path_url = f"{path}?{query_string}"
        message = f"{method.upper()}{path_url}"
        
        if body:
            message += json.dumps(body, separators=(',', ':'))
            
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature, timestamp, p

    def _request(self, method, path, params=None, body=None, auth=False):
        url = f"{BASE_URL}{path}"
        headers = {"Content-Type": "application/json"}
        req_params = params.copy() if params else {}
        
        if auth:
            if not self.api_key or not self.api_secret:
                raise PionexAPIError("API Key and Secret required for authenticated endpoints.")
            signature, timestamp, req_params = self._generate_signature(method, path, params, body)
            headers["PIONEX-KEY"] = self.api_key
            headers["PIONEX-SIGNATURE"] = signature
        
        last_err = None
        for attempt in range(self.max_retries):
            try:
                if method == "GET":
                    resp = self.session.get(url, params=req_params, headers=headers, timeout=self.timeout)
                elif method == "POST":
                    resp = self.session.post(url, params=req_params, json=body, headers=headers, timeout=self.timeout)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                    
                resp.raise_for_status()
                data = resp.json()
                if not data.get("result", False):
                    raise PionexAPIError(f"API returned result=false: {data}")
                return data["data"]
            except (requests.RequestException, PionexAPIError, ValueError) as e:
                last_err = e
                time.sleep(0.5 * (attempt + 1))
        raise PionexAPIError(f"Failed after {self.max_retries} attempts: {last_err}")

    # --- PUBLIC MARKET DATA ---

    def get_book_ticker(self, symbol: str, type_: str = "SPOT"):
        data = self._request("GET", "/api/v1/market/bookTickers", {"symbol": symbol, "type": type_})
        tickers = data.get("tickers", [])
        if not tickers:
            raise PionexAPIError(f"No book ticker returned for {symbol}")
        return tickers[0]

    def get_depth(self, symbol: str, limit: int = 20):
        return self._request("GET", "/api/v1/market/depth", {"symbol": symbol, "limit": limit})

    def get_trades(self, symbol: str, limit: int = 100):
        data = self._request("GET", "/api/v1/market/trades", {"symbol": symbol, "limit": limit})
        return data.get("trades", [])

    def get_klines(self, symbol: str, interval: str = "1M", limit: int = 100):
        data = self._request("GET", "/api/v1/market/klines", {"symbol": symbol, "interval": interval, "limit": limit})
        return data.get("klines", [])

    # --- PRIVATE EXECUTION ---
    
    def create_order(self, symbol: str, side: str, type_: str, size: float = None, price: float = None, amount: float = None):
        """
        side: BUY or SELL
        type_: LIMIT or MARKET
        size: base currency quantity (e.g., BTC amount)
        price: for LIMIT orders
        amount: quote currency quantity (e.g., USDT amount) for MARKET BUY
        """
        body = {
            "symbol": symbol,
            "side": side.upper(),
            "type": type_.upper()
        }
        if size is not None:
            body["size"] = str(size)
        if price is not None:
            body["price"] = str(price)
        if amount is not None:
            body["amount"] = str(amount)
            
        return self._request("POST", "/api/v1/trade/order", body=body, auth=True)
        
    def get_order(self, order_id: str):
        return self._request("GET", "/api/v1/trade/order", params={"orderId": order_id}, auth=True)

    def get_balances(self):
        data = self._request("GET", "/api/v1/account/balances", auth=True)
        return data.get("balances", [])
