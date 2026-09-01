"""Offline freqtrade runner stubbed for US STOCKS as TICKER/USD spot markets.

Same offline approach as run_backtest.py, but the stubbed markets are equities
(AAPL/USD, MSFT/USD, ...) on a USD-quote spot exchange (kraken is used only as a
freqtrade-supported host for the stub — no network is touched). OHLCV comes from
local feathers built by tools/fetch_stocks.py; indicators/accounting stay real.

Usage:
    python run_backtest_stocks.py backtesting --config user_data/config_stocks.json \
        --datadir user_data/data_stocks/kraken --timeframe 1d --timerange 20180101- --cache none
"""
import sys
import ccxt
import ccxt.async_support as ccxt_async

# Edit this list to match the tickers you fetched.
TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "SPY", "QQQ"]


def _mkt(base):
    return {
        "id": f"{base}USD", "lowercaseId": f"{base.lower()}usd", "symbol": f"{base}/USD",
        "base": base, "quote": "USD", "settle": None,
        "baseId": base, "quoteId": "USD", "settleId": None,
        "type": "spot", "spot": True, "margin": False, "swap": False, "future": False,
        "option": False, "index": None, "active": True, "contract": False,
        "linear": None, "inverse": None, "subType": None,
        "taker": 0.0005, "maker": 0.0005, "percentage": True, "tierBased": False,
        "feeSide": "get", "contractSize": None,
        "expiry": None, "expiryDatetime": None, "strike": None, "optionType": None,
        "precision": {"amount": 1e-06, "price": 0.01, "base": 1e-08, "quote": 1e-08},
        "limits": {
            "leverage": {"min": None, "max": None},
            "amount": {"min": 1e-06, "max": 1e9},
            "price": {"min": 0.01, "max": 1e7},
            "cost": {"min": 1.0, "max": 1e9},
            "market": {"min": 0.0, "max": 1e7},
        },
        "created": None, "info": {},
    }


MARKETS_LIST = [_mkt(t) for t in TICKERS]


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


_patch(ccxt.kraken)
_patch_async(ccxt_async.kraken)

from freqtrade.main import main  # noqa: E402

if __name__ == "__main__":
    sys.argv = ["freqtrade"] + sys.argv[1:]
    main()
