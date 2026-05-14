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


def test_forward_fill_when_no_data_available(tmp_path, monkeypatch):
    from datetime import date
    import pandas as pd
    from data.provider import DataProvider

    monkeypatch.setattr('data.finmind.FinMindAdapter.fetch_ohlcv',
                        lambda self, t, s, e: pd.DataFrame())
    monkeypatch.setattr('data.yfinance_src.YFinanceAdapter.fetch_ohlcv',
                        lambda self, t, s, e: pd.DataFrame())

    provider = DataProvider(cache_dir=str(tmp_path))
    seed = pd.DataFrame([{
        'ticker': '2330', 'date': '2025-01-02',
        'open': 600, 'high': 605, 'low': 595, 'close': 600, 'volume': 1000,
        'quality_flag': 'clean',
    }])
    provider.cache.save_ohlcv('2330', seed, source='finmind')

    out = provider.get_ohlcv('2330', date(2025, 1, 2), date(2025, 1, 3))
    assert out is not None
    rows = out[out['date'] == '2025-01-03']
    assert not rows.empty
    assert rows.iloc[0]['quality_flag'] == 'forward_filled'
    assert rows.iloc[0]['close'] == 600


def test_yfinance_fallback_marks_quality_flag(tmp_path, monkeypatch):
    from datetime import date
    import pandas as pd
    from data.provider import DataProvider

    yf_data = pd.DataFrame([
        {'ticker': '2330', 'date': '2025-01-02', 'open': 600, 'high': 605,
         'low': 595, 'close': 600, 'volume': 1000},
    ])
    monkeypatch.setattr('data.finmind.FinMindAdapter.fetch_ohlcv',
                        lambda self, t, s, e: pd.DataFrame())
    monkeypatch.setattr('data.yfinance_src.YFinanceAdapter.fetch_ohlcv',
                        lambda self, t, s, e: yf_data.copy())

    provider = DataProvider(cache_dir=str(tmp_path))
    out = provider.get_ohlcv('2330', date(2025, 1, 2), date(2025, 1, 2))
    assert out is not None
    assert (out['quality_flag'] == 'yfinance').all()


def test_overlapping_finmind_and_yfinance_does_not_violate_unique_pk(tmp_path, monkeypatch):
    """Regression: both adapters returning the same dates must not cause SQLite
    UNIQUE constraint failure on (ticker, date)."""
    from datetime import date
    import pandas as pd
    from data.provider import DataProvider

    rows = [
        {'ticker': '00631L', 'date': '2026-01-02', 'open': 100, 'high': 105,
         'low': 95, 'close': 100, 'volume': 1000},
        {'ticker': '00631L', 'date': '2026-01-05', 'open': 102, 'high': 108,
         'low': 100, 'close': 105, 'volume': 1200},
    ]
    fm_df = pd.DataFrame(rows)
    yf_df = pd.DataFrame(rows)

    monkeypatch.setattr('data.finmind.FinMindAdapter.fetch_ohlcv',
                        lambda self, t, s, e: fm_df.copy())
    monkeypatch.setattr('data.yfinance_src.YFinanceAdapter.fetch_ohlcv',
                        lambda self, t, s, e: yf_df.copy())

    provider = DataProvider(cache_dir=str(tmp_path))
    out = provider.get_ohlcv('00631L', date(2026, 1, 2), date(2026, 1, 5))
    assert out is not None
    assert len(out) == 2
    assert out['date'].is_unique
    assert (out['quality_flag'] == 'clean').all()
