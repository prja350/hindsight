from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import date
from data.yfinance_src import YFinanceAdapter


def _mock_history():
    idx = pd.to_datetime(['2023-01-03', '2023-01-04', '2023-01-05'])
    return pd.DataFrame({
        'Open': [500.0, 505.0, 498.0], 'High': [510.0, 510.0, 505.0],
        'Low':  [498.0, 500.0, 490.0], 'Close': [505.0, 498.0, 492.0],
        'Volume': [1_500_000, 1_200_000, 1_800_000],
    }, index=idx)


def test_fetch_ohlcv_normalized_columns():
    adapter = YFinanceAdapter()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = _mock_history()
    with patch('yfinance.Ticker', return_value=mock_ticker):
        df = adapter.fetch_ohlcv('2330', date(2023, 1, 3), date(2023, 1, 5))
    assert set(df.columns) >= {'ticker', 'date', 'open', 'high', 'low', 'close', 'volume'}
    assert len(df) == 3


def test_fetch_ohlcv_adds_tw_suffix():
    adapter = YFinanceAdapter()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = _mock_history()
    with patch('yfinance.Ticker') as mock_cls:
        mock_cls.return_value = mock_ticker
        adapter.fetch_ohlcv('2330', date(2023, 1, 3), date(2023, 1, 5))
        mock_cls.assert_called_once_with('2330.TW')


def test_fetch_ohlcv_empty_returns_empty_df():
    adapter = YFinanceAdapter()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()
    with patch('yfinance.Ticker', return_value=mock_ticker):
        df = adapter.fetch_ohlcv('9999', date(2023, 1, 1), date(2023, 1, 5))
    assert df.empty
