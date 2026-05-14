import pytest
import pandas as pd
from datetime import date
from data.cache import CacheManager


@pytest.fixture
def cache(tmp_path):
    return CacheManager(db_path=str(tmp_path / "test.db"))


def test_ohlcv_miss_returns_none(cache):
    assert cache.get_ohlcv("2330", date(2023, 1, 1), date(2023, 1, 5)) is None


def test_ohlcv_save_and_retrieve(cache, sample_ohlcv_df):
    cache.save_ohlcv("2330", sample_ohlcv_df, source="finmind")
    result = cache.get_ohlcv("2330", date(2023, 1, 3), date(2023, 1, 6))
    assert result is not None
    assert len(result) == 4


def test_ohlcv_save_replaces_existing_rows(cache, sample_ohlcv_df):
    cache.save_ohlcv("2330", sample_ohlcv_df, source="finmind")
    updated = sample_ohlcv_df.copy()
    updated.loc[updated['date'] == '2023-01-03', 'close'] = 999.0
    cache.save_ohlcv("2330", updated, source="finmind")
    result = cache.get_ohlcv("2330", date(2023, 1, 3), date(2023, 1, 3))
    assert result['close'].iloc[0] == 999.0


def test_fundamentals_miss_returns_none(cache):
    assert cache.get_fundamentals("2330", date(2023, 1, 1), date(2023, 1, 5)) is None


def test_fundamentals_save_and_retrieve(cache, sample_fundamentals_df):
    cache.save_fundamentals("2330", sample_fundamentals_df, source="finmind")
    result = cache.get_fundamentals("2330", date(2023, 1, 3), date(2023, 1, 5))
    assert result is not None
    assert len(result) == 3


def test_ticker_list_miss_returns_none(cache):
    assert cache.get_ticker_list() is None


def test_ticker_list_save_and_retrieve(cache, sample_ticker_list_df):
    cache.save_ticker_list(sample_ticker_list_df, source="finmind")
    result = cache.get_ticker_list()
    assert result is not None
    assert len(result) == 3


def test_is_fresh_after_save(cache, sample_ohlcv_df):
    assert not cache.is_fresh("2330", "ohlcv")
    cache.save_ohlcv("2330", sample_ohlcv_df, source="finmind")
    assert cache.is_fresh("2330", "ohlcv")


def test_ohlcv_has_quality_flag_column(cache):
    with cache._conn() as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(ohlcv)").fetchall()]
    assert "quality_flag" in cols


def test_save_with_quality_flag(cache, sample_ohlcv_df):
    df = sample_ohlcv_df.copy()
    df["quality_flag"] = ["clean", "clean", "yfinance", "forward_filled", "clean"]
    cache.save_ohlcv("2330", df, source="finmind")
    result = cache.get_ohlcv("2330", date(2023, 1, 3), date(2023, 1, 9))
    assert result is not None
    assert "quality_flag" in result.columns
    flags = result.sort_values("date")["quality_flag"].tolist()
    assert flags == ["clean", "clean", "yfinance", "forward_filled", "clean"]


def test_save_default_quality_flag_when_missing(cache, sample_ohlcv_df):
    cache.save_ohlcv("2330", sample_ohlcv_df, source="finmind")
    result = cache.get_ohlcv("2330", date(2023, 1, 3), date(2023, 1, 9))
    assert result is not None
    assert (result["quality_flag"] == "clean").all()


def test_legacy_db_migrates_quality_flag(tmp_path):
    """CacheManager opening a pre-existing db without quality_flag column adds it."""
    import sqlite3
    db = tmp_path / "legacy.db"
    with sqlite3.connect(db) as conn:
        conn.executescript("""
            CREATE TABLE ohlcv (
                ticker TEXT, date TEXT,
                open REAL, high REAL, low REAL, close REAL, volume INTEGER,
                PRIMARY KEY (ticker, date)
            );
            INSERT INTO ohlcv VALUES ('2330', '2023-01-03', 500.0, 510.0, 498.0, 505.0, 1500000);
        """)
    cache = CacheManager(db_path=str(db))
    with cache._conn() as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(ohlcv)").fetchall()]
    assert "quality_flag" in cols
