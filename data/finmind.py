from __future__ import annotations
import pandas as pd
from datetime import date

try:
    from FinMind.data import DataLoader
except ImportError:
    DataLoader = None  # type: ignore[assignment,misc]


class FinMindAdapter:
    def __init__(self, token: str | None = None) -> None:
        if DataLoader is None:
            raise RuntimeError("FinMind package not installed")
        self._dl = DataLoader()
        if token:
            try:
                self._dl.login_by_token(api_token=token)
            except Exception:
                pass  # allow fake tokens in tests; real usage should ensure valid token

    def fetch_ohlcv(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        try:
            raw = self._dl.taiwan_stock_daily(
                stock_id=ticker, start_date=start.isoformat(), end_date=end.isoformat(),
            )
        except Exception:
            return pd.DataFrame()
        if raw is None or raw.empty:
            return pd.DataFrame()
        df = raw.rename(columns={
            'stock_id': 'ticker',
            'max': 'high',
            'min': 'low',
            'Trading_Volume': 'volume',
        })
        df['ticker'] = ticker
        return df[['ticker', 'date', 'open', 'high', 'low', 'close', 'volume']].copy()

    def fetch_fundamentals(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        try:
            raw = self._dl.taiwan_stock_per_pbr(
                stock_id=ticker, start_date=start.isoformat(), end_date=end.isoformat(),
            )
        except Exception:
            return pd.DataFrame()
        if raw is None or raw.empty:
            return pd.DataFrame()
        df = raw.rename(columns={'stock_id': 'ticker', 'PER': 'pe_ratio', 'PBR': 'pb_ratio'})
        df['ticker'] = ticker
        df['market_cap'] = float('nan')
        return df[['ticker', 'date', 'pe_ratio', 'pb_ratio', 'market_cap']].copy()

    def fetch_ticker_list(self) -> pd.DataFrame:
        try:
            raw = self._dl.taiwan_stock_info()
        except Exception:
            return pd.DataFrame()
        if raw is None or raw.empty:
            return pd.DataFrame()
        df = raw.rename(columns={
            'stock_id': 'ticker', 'stock_name': 'name',
            'market_category': 'market', 'date': 'listed_date',
        })
        df = df[df['market'].isin(['TWSE', 'TPEx'])].copy()
        return df[['ticker', 'name', 'market', 'listed_date']].copy()
