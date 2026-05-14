from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
from datetime import date
from data.finmind import FinMindAdapter


@pytest.fixture
def adapter():
    return FinMindAdapter(token="fake-token")


def _mock_ohlcv():
    return pd.DataFrame({
        'stock_id': ['2330'] * 3,
        'date':     ['2023-01-03', '2023-01-04', '2023-01-05'],
        'open': [500.0, 505.0, 498.0], 'max': [510.0, 510.0, 505.0],
        'min': [498.0, 500.0, 490.0],  'close': [505.0, 498.0, 492.0],
        'Trading_Volume': [1_500_000, 1_200_000, 1_800_000],
    })


def test_fetch_ohlcv_normalized_columns(adapter):
    with patch.object(adapter._dl, 'taiwan_stock_daily', return_value=_mock_ohlcv()):
        df = adapter.fetch_ohlcv('2330', date(2023, 1, 3), date(2023, 1, 5))
    assert set(df.columns) >= {'ticker', 'date', 'open', 'high', 'low', 'close', 'volume'}
    assert df['ticker'].iloc[0] == '2330'
    assert len(df) == 3


def test_fetch_ohlcv_empty_returns_empty_df(adapter):
    with patch.object(adapter._dl, 'taiwan_stock_daily', return_value=pd.DataFrame()):
        df = adapter.fetch_ohlcv('9999', date(2023, 1, 1), date(2023, 1, 5))
    assert df.empty


def test_fetch_fundamentals_normalized_columns(adapter):
    mock_data = pd.DataFrame({
        'stock_id': ['2330'] * 2, 'date': ['2023-01-03', '2023-01-04'],
        'PER': [15.2, 15.5], 'PBR': [5.1, 5.2],
    })
    with patch.object(adapter._dl, 'taiwan_stock_per_pbr', return_value=mock_data):
        df = adapter.fetch_fundamentals('2330', date(2023, 1, 3), date(2023, 1, 4))
    assert set(df.columns) >= {'ticker', 'date', 'pe_ratio', 'pb_ratio'}


def test_fetch_ticker_list_normalized_columns(adapter):
    mock_data = pd.DataFrame({
        'stock_id': ['2330'], 'stock_name': ['台積電'],
        'market_category': ['TWSE'], 'date': ['1994-09-05'],
    })
    with patch.object(adapter._dl, 'taiwan_stock_info', return_value=mock_data):
        df = adapter.fetch_ticker_list()
    assert set(df.columns) >= {'ticker', 'name', 'market', 'listed_date'}
