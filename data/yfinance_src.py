from __future__ import annotations
import pandas as pd
from datetime import date
import yfinance as yf


class YFinanceAdapter:
    def fetch_ohlcv(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        try:
            raw = yf.Ticker(f"{ticker}.TW").history(
                start=start.isoformat(), end=end.isoformat(),
            )
        except Exception:
            return pd.DataFrame()
        if raw is None or raw.empty:
            return pd.DataFrame()
        raw.index.name = 'Date'
        raw = raw.reset_index()
        df = raw.rename(columns={
            'Date': 'date', 'Open': 'open', 'High': 'high',
            'Low': 'low', 'Close': 'close', 'Volume': 'volume',
        })
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        df['ticker'] = ticker
        return df[['ticker', 'date', 'open', 'high', 'low', 'close', 'volume']].copy()
