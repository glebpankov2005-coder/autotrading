"""Offline freqtrade runner stubbed for BTC/ETH/SOL USDT-margined PERPETUAL swaps.

Same offline approach as run_backtest_2y.py but the stubbed markets are linear
perpetual swaps (BTC/USDT:USDT) so freqtrade can backtest in futures mode
(long + short). Funding/mark come from local feather data (funding stubbed to 0).
"""
import sys
import ccxt
import ccxt.async_support as ccxt_async


def _swap(base):
    return {
        "id": f"{base}USDT", "lowercaseId": f"{base.lower()}usdt", "symbol": f"{base}/USDT:USDT",
        "base": base, "quote": "USDT", "settle": "USDT",
        "baseId": base, "quoteId": "USDT", "settleId": "USDT",
        "type": "swap", "spot": False, "margin": False, "swap": True, "future": False,
        "option": False, "index": None, "active": True, "contract": True,
        "linear": True, "inverse": False, "subType": "linear",
        "taker": 0.0004, "maker": 0.0002, "percentage": True, "tierBased": True,
        "feeSide": "get", "contractSize": 1.0,
        "expiry": None, "expiryDatetime": None, "strike": None, "optionType": None,
        "precision": {"amount": 0.001, "price": 0.01, "base": 1e-08, "quote": 1e-08},
        "limits": {
            "leverage": {"min": 1.0, "max": 125.0},
            "amount": {"min": 0.001, "max": 10000.0},
            "price": {"min": 0.01, "max": 1000000.0},
            "cost": {"min": 5.0, "max": None},
            "market": {"min": 0.001, "max": 1000.0},
        },
        "created": None, "info": {},
    }


MARKETS = [_swap("BTC"), _swap("ETH"), _swap("SOL")]

# minimal leverage-tier table so futures margin maths has data
def _tiers():
    t = {}
    for m in MARKETS:
        t[m["symbol"]] = [
            {"tier": 1, "minNotional": 0, "maxNotional": 50000, "maintenanceMarginRate": 0.004,
             "maxLeverage": 125, "info": {}},
            {"tier": 2, "minNotional": 50000, "maxNotional": 250000, "maintenanceMarginRate": 0.005,
             "maxLeverage": 100, "info": {}},
        ]
    return t


def _patch(cls, is_async):
    def fetch_markets(self, params={}):
        return MARKETS
    def fetch_currencies(self, params={}):
        return {}
    def load_time_difference(self, params={}):
        self.options["timeDifference"] = 0
        return 0
    def fetch_leverage_tiers(self, symbols=None, params={}):
        return _tiers()
    if is_async:
        async def afetch_markets(self, params={}): return MARKETS
        async def afetch_currencies(self, params={}): return {}
        async def aload_time_difference(self, params={}):
            self.options["timeDifference"] = 0; return 0
        async def afetch_leverage_tiers(self, symbols=None, params={}): return _tiers()
        cls.fetch_markets = afetch_markets; cls.fetch_currencies = afetch_currencies
        cls.load_time_difference = aload_time_difference; cls.fetch_leverage_tiers = afetch_leverage_tiers
    else:
        cls.fetch_markets = fetch_markets; cls.fetch_currencies = fetch_currencies
        cls.load_time_difference = load_time_difference; cls.fetch_leverage_tiers = fetch_leverage_tiers


_patch(ccxt.binance, False)
_patch(ccxt_async.binance, True)

from freqtrade.main import main  # noqa: E402

if __name__ == "__main__":
    sys.argv = ["freqtrade"] + sys.argv[1:]
    main()
