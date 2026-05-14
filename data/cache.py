from __future__ import annotations
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional
import pandas as pd

_TTL: dict[str, Optional[int]] = {
    "ohlcv":        None,  # permanent
    "fundamentals": 7,
    "ticker_list":  30,
}


class CacheManager:
    def __init__(self, db_path: str = "data/db/hindsight.db") -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS ohlcv (
                    ticker TEXT, date TEXT,
                    open REAL, high REAL, low REAL, close REAL, volume INTEGER,
                    quality_flag TEXT NOT NULL DEFAULT 'clean',
                    PRIMARY KEY (ticker, date)
                );
                CREATE TABLE IF NOT EXISTS fundamentals (
                    ticker TEXT, date TEXT,
                    pe_ratio REAL, pb_ratio REAL, market_cap REAL,
                    PRIMARY KEY (ticker, date)
                );
                CREATE TABLE IF NOT EXISTS cache_meta (
                    ticker TEXT, data_type TEXT,
                    last_updated TEXT, source TEXT,
                    PRIMARY KEY (ticker, data_type)
                );
                CREATE TABLE IF NOT EXISTS ticker_list (
                    ticker TEXT PRIMARY KEY, name TEXT,
                    market TEXT, listed_date TEXT
                );
            """)
            try:
                conn.execute(
                    "ALTER TABLE ohlcv ADD COLUMN quality_flag TEXT NOT NULL DEFAULT 'clean'"
                )
            except sqlite3.OperationalError:
                pass

    def is_fresh(self, ticker: str, data_type: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT last_updated FROM cache_meta WHERE ticker=? AND data_type=?",
                (ticker, data_type),
            ).fetchone()
        if row is None:
            return False
        ttl = _TTL.get(data_type)
        if ttl is None:
            return True
        age = (datetime.now() - datetime.fromisoformat(row["last_updated"])).days
        return age < ttl

    def _meta_update(self, conn: sqlite3.Connection, ticker: str, data_type: str, source: str) -> None:
        conn.execute(
            "INSERT OR REPLACE INTO cache_meta VALUES (?, ?, ?, ?)",
            (ticker, data_type, datetime.now().isoformat(), source),
        )

    def get_ohlcv(self, ticker: str, start: date, end: date) -> Optional[pd.DataFrame]:
        if not self.is_fresh(ticker, "ohlcv"):
            return None
        with self._conn() as conn:
            df = pd.read_sql(
                "SELECT * FROM ohlcv WHERE ticker=? AND date>=? AND date<=? ORDER BY date",
                conn, params=(ticker, start.isoformat(), end.isoformat()),
            )
        return df if not df.empty else None

    def save_ohlcv(self, ticker: str, df: pd.DataFrame, source: str) -> None:
        if df.empty:
            return
        df = df.copy()
        if 'quality_flag' not in df.columns:
            df['quality_flag'] = 'clean'
        df = df[['ticker', 'date', 'open', 'high', 'low', 'close', 'volume', 'quality_flag']].copy()
        df['ticker'] = ticker
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM ohlcv WHERE ticker=? AND date>=? AND date<=?",
                (ticker, df['date'].min(), df['date'].max()),
            )
            df.to_sql('ohlcv', conn, if_exists='append', index=False)
            self._meta_update(conn, ticker, "ohlcv", source)

    def get_fundamentals(self, ticker: str, start: date, end: date) -> Optional[pd.DataFrame]:
        if not self.is_fresh(ticker, "fundamentals"):
            return None
        with self._conn() as conn:
            df = pd.read_sql(
                "SELECT * FROM fundamentals WHERE ticker=? AND date>=? AND date<=? ORDER BY date",
                conn, params=(ticker, start.isoformat(), end.isoformat()),
            )
        return df if not df.empty else None

    def save_fundamentals(self, ticker: str, df: pd.DataFrame, source: str) -> None:
        if df.empty:
            return
        df = df[['ticker', 'date', 'pe_ratio', 'pb_ratio', 'market_cap']].copy()
        df['ticker'] = ticker
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM fundamentals WHERE ticker=? AND date>=? AND date<=?",
                (ticker, df['date'].min(), df['date'].max()),
            )
            df.to_sql('fundamentals', conn, if_exists='append', index=False)
            self._meta_update(conn, ticker, "fundamentals", source)

    def get_ticker_list(self) -> Optional[pd.DataFrame]:
        if not self.is_fresh("__all__", "ticker_list"):
            return None
        with self._conn() as conn:
            df = pd.read_sql("SELECT * FROM ticker_list", conn)
        return df if not df.empty else None

    def save_ticker_list(self, df: pd.DataFrame, source: str) -> None:
        if df.empty:
            return
        df = df[['ticker', 'name', 'market', 'listed_date']].copy()
        with self._conn() as conn:
            conn.execute("DELETE FROM ticker_list")
            df.to_sql('ticker_list', conn, if_exists='append', index=False)
            self._meta_update(conn, "__all__", "ticker_list", source)
