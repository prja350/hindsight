from unittest.mock import MagicMock
import pandas as pd
import pytest
from datetime import date
from data.provider import DataProvider


@pytest.fixture
def provider(tmp_path):
    p = DataProvider(cache_dir=str(tmp_path), finmind_token=None)
    return p


def test_get_ohlcv_hits_cache_on_second_call(provider, sample_ohlcv_df):
    provider.cache.save_ohlcv('2330', sample_ohlcv_df, source='finmind')
    result = provider.get_ohlcv('2330', date(2023, 1, 3), date(2023, 1, 9))
    assert result is not None
    assert len(result) == 5


def test_get_ohlcv_falls_back_to_yfinance_when_finmind_empty(provider, sample_ohlcv_df):
    provider.finmind.fetch_ohlcv = MagicMock(return_value=pd.DataFrame())
    provider.yfinance.fetch_ohlcv = MagicMock(return_value=sample_ohlcv_df)
    result = provider.get_ohlcv('2330', date(2023, 1, 3), date(2023, 1, 9))
    assert result is not None
    provider.yfinance.fetch_ohlcv.assert_called_once()


def test_get_ohlcv_saves_to_cache_after_fetch(provider, sample_ohlcv_df):
    provider.finmind.fetch_ohlcv = MagicMock(return_value=sample_ohlcv_df)
    provider.get_ohlcv('2330', date(2023, 1, 3), date(2023, 1, 9))
    assert provider.cache.is_fresh('2330', 'ohlcv')


def test_get_ohlcv_returns_none_when_both_fail(provider):
    provider.finmind.fetch_ohlcv = MagicMock(return_value=pd.DataFrame())
    provider.yfinance.fetch_ohlcv = MagicMock(return_value=pd.DataFrame())
    assert provider.get_ohlcv('2330', date(2023, 1, 3), date(2023, 1, 9)) is None


def test_get_ticker_list_uses_cache(provider, sample_ticker_list_df):
    provider.cache.save_ticker_list(sample_ticker_list_df, source='finmind')
    result = provider.get_ticker_list()
    assert result is not None
    assert len(result) == 3
