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
        from data.calendar import trading_days
        from data.quality import detect_gaps

        expected = trading_days(start, end)
        if not expected:
            return None

        cached = self.cache.get_ohlcv(ticker, start, end)
        if cached is None:
            cached = pd.DataFrame(columns=[
                'ticker', 'date', 'open', 'high', 'low', 'close', 'volume', 'quality_flag',
            ])

        if 'quality_flag' in cached.columns:
            cached = cached[cached['quality_flag'] != 'forward_filled'].reset_index(drop=True)

        gaps = detect_gaps(cached, expected)
        new_rows: list[pd.DataFrame] = []

        for gap_start, gap_end in gaps:
            fm = self.finmind.fetch_ohlcv(ticker, gap_start, gap_end)
            covered: set[str] = set()
            if fm is not None and not fm.empty:
                fm = fm.assign(quality_flag='clean')
                new_rows.append(fm)
                covered = set(fm['date'].astype(str).tolist())

            remaining = [d for d in expected
                         if gap_start <= d <= gap_end and d.isoformat() not in covered]
            if remaining:
                yf = self.yfinance.fetch_ohlcv(ticker, gap_start, gap_end)
                if yf is not None and not yf.empty:
                    yf = yf.assign(quality_flag='yfinance')
                    new_rows.append(yf)
                    covered |= set(yf['date'].astype(str).tolist())
                still_missing = [d for d in remaining if d.isoformat() not in covered]
                if still_missing:
                    fill = self._forward_fill(ticker, cached, new_rows, still_missing)
                    if not fill.empty:
                        new_rows.append(fill)

        if new_rows:
            merged = pd.concat([cached] + new_rows, ignore_index=True)
            self.cache.save_ohlcv(ticker, merged, source='multi')
            return self.cache.get_ohlcv(ticker, start, end)

        return cached if not cached.empty else None

    def _forward_fill(self, ticker, cached_df, new_rows, missing_dates):
        parts = [cached_df] + new_rows if new_rows else [cached_df]
        all_known = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
        if all_known.empty:
            return pd.DataFrame()
        all_known = all_known.sort_values('date').reset_index(drop=True)
        rows = []
        for d in missing_dates:
            prior = all_known[all_known['date'] < d.isoformat()]
            if prior.empty:
                continue
            last_close = float(prior.iloc[-1]['close'])
            rows.append({
                'ticker': ticker, 'date': d.isoformat(),
                'open': last_close, 'high': last_close, 'low': last_close,
                'close': last_close, 'volume': 0, 'quality_flag': 'forward_filled',
            })
        return pd.DataFrame(rows)

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
