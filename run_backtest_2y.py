"""Offline freqtrade runner stubbed for BTC/USDT + ETH/USDT spot (2-year tourney).

Same approach as run_backtest.py: feed ccxt static market metadata for both pairs
so freqtrade never touches the network. OHLCV/indicators/accounting stay real.
"""
import sys

import ccxt
import ccxt.async_support as ccxt_async


def _mkt(base):
    return {
        "id": f"{base}USDT", "lowercaseId": f"{base.lower()}usdt", "symbol": f"{base}/USDT",
        "base": base, "quote": "USDT", "settle": None,
        "baseId": base, "quoteId": "USDT", "settleId": None,
        "type": "spot", "spot": True, "margin": True, "swap": False, "future": False,
        "option": False, "index": None, "active": True, "contract": False,
        "linear": None, "inverse": None, "subType": None,
        "taker": 0.001, "maker": 0.001, "percentage": True, "tierBased": False,
        "feeSide": "get", "contractSize": None,
        "expiry": None, "expiryDatetime": None, "strike": None, "optionType": None,
        "precision": {"amount": 1e-05, "price": 0.01, "base": 1e-08, "quote": 1e-08},
        "limits": {
            "leverage": {"min": None, "max": None},
            "amount": {"min": 1e-05, "max": 9000.0},
            "price": {"min": 0.01, "max": 1000000.0},
            "cost": {"min": 5.0, "max": 9000000.0},
            "market": {"min": 0.0, "max": 3200.0},
        },
        "created": None, "info": {},
    }


MARKETS_LIST = [_mkt("BTC"), _mkt("ETH"), _mkt("SOL")]


def _patch(cls):
    def fetch_markets(self, params={}):
        return MARKETS_LIST

    def fetch_currencies(self, params={}):
        return {}

    def load_time_difference(self, params={}):
        self.options["timeDifference"] = 0
        return 0

    cls.fetch_markets = fetch_markets
    cls.fetch_currencies = fetch_currencies
    cls.load_time_difference = load_time_difference


def _patch_async(cls):
    async def fetch_markets(self, params={}):
        return MARKETS_LIST

    async def fetch_currencies(self, params={}):
        return {}

    async def load_time_difference(self, params={}):
        self.options["timeDifference"] = 0
        return 0

    cls.fetch_markets = fetch_markets
    cls.fetch_currencies = fetch_currencies
    cls.load_time_difference = load_time_difference


_patch(ccxt.binance)
_patch_async(ccxt_async.binance)

from freqtrade.main import main  # noqa: E402

if __name__ == "__main__":
    sys.argv = ["freqtrade"] + sys.argv[1:]
    main()
