from __future__ import annotations
import os
from datetime import date
from typing import Optional
import pandas as pd

from data.cache import CacheManager
from data.finmind import FinMindAdapter
from data.yfinance_src import YFinanceAdapter


class DataProvider:
    def __init__(self, cache_dir: str | None = None, finmind_token: str | None = None) -> None:
        cache_dir = cache_dir or os.getenv("CACHE_DIR", "data/db")
        finmind_token = finmind_token or os.getenv("FINMIND_TOKEN")
        self.cache = CacheManager(db_path=f"{cache_dir}/hindsight.db")
        self.finmind = FinMindAdapter(token=finmind_token)
        self.yfinance = YFinanceAdapter()

    def get_ohlcv(self, ticker: str, start: date, end: date) -> Optional[pd.DataFrame]:
        cached = self.cache.get_ohlcv(ticker, start, end)
        if cached is not None:
            return cached
        df = self.finmind.fetch_ohlcv(ticker, start, end)
        source = "finmind"
        if df.empty:
            df = self.yfinance.fetch_ohlcv(ticker, start, end)
            source = "yfinance"
        if df.empty:
            return None
        self.cache.save_ohlcv(ticker, df, source=source)
        return self.cache.get_ohlcv(ticker, start, end)

    def get_fundamentals(self, ticker: str, start: date, end: date) -> Optional[pd.DataFrame]:
        cached = self.cache.get_fundamentals(ticker, start, end)
        if cached is not None:
            return cached
        df = self.finmind.fetch_fundamentals(ticker, start, end)
        if df.empty:
            return None
        self.cache.save_fundamentals(ticker, df, source="finmind")
        return self.cache.get_fundamentals(ticker, start, end)

    def get_ticker_list(self) -> Optional[pd.DataFrame]:
        cached = self.cache.get_ticker_list()
        if cached is not None:
            return cached
        df = self.finmind.fetch_ticker_list()
        if df.empty:
            return None
        self.cache.save_ticker_list(df, source="finmind")
        return self.cache.get_ticker_list()
