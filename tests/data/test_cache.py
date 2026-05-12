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
