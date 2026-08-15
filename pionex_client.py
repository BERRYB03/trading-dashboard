"""
Pionex public market-data client.

Uses only the documented PUBLIC endpoints (no API key required):
https://www.pionex.com/docs/api-docs/trade-api/market

These return real, live exchange data. Nothing in this file is simulated.
"""

import time
import requests

BASE_URL = "https://api.pionex.com"


class PionexAPIError(Exception):
    pass


class PionexClient:
    def __init__(self, timeout=5, max_retries=3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()

    def _get(self, path, params=None):
        url = f"{BASE_URL}{path}"
        last_err = None
        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                if not data.get("result", False):
                    raise PionexAPIError(f"API returned result=false: {data}")
                return data["data"]
            except (requests.RequestException, PionexAPIError, ValueError) as e:
                last_err = e
                time.sleep(0.5 * (attempt + 1))
        raise PionexAPIError(f"Failed after {self.max_retries} attempts: {last_err}")

    def get_book_ticker(self, symbol: str, type_: str = "PERP"):
        """Best bid/ask. Returns dict with bidPrice, bidSize, askPrice, askSize, timestamp (all real)."""
        data = self._get("/api/v1/market/bookTickers", {"symbol": symbol, "type": type_})
        tickers = data.get("tickers", [])
        if not tickers:
            raise PionexAPIError(f"No book ticker returned for {symbol}")
        return tickers[0]

    def get_depth(self, symbol: str, limit: int = 20):
        """Order book snapshot: real bids/asks as [price, quantity] pairs."""
        return self._get("/api/v1/market/depth", {"symbol": symbol, "limit": limit})

    def get_trades(self, symbol: str, limit: int = 100):
        """Recent executed trades on the real order book."""
        data = self._get("/api/v1/market/trades", {"symbol": symbol, "limit": limit})
        return data.get("trades", [])

    def get_klines(self, symbol: str, interval: str = "1M", limit: int = 100):
        """Real OHLCV candles. interval in: 1M,5M,15M,30M,60M,4H,8H,12H,1D"""
        data = self._get("/api/v1/market/klines", {"symbol": symbol, "interval": interval, "limit": limit})
        return data.get("klines", [])
