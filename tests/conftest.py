import pytest
import pandas as pd
from datetime import date


@pytest.fixture
def sample_ohlcv_df():
    return pd.DataFrame({
        'ticker': ['2330'] * 5,
        'date':   ['2023-01-03', '2023-01-04', '2023-01-05', '2023-01-06', '2023-01-09'],
        'open':   [500.0, 505.0, 498.0, 492.0, 488.0],
        'high':   [510.0, 510.0, 505.0, 498.0, 495.0],
        'low':    [498.0, 500.0, 490.0, 486.0, 482.0],
        'close':  [505.0, 498.0, 492.0, 488.0, 490.0],
        'volume': [1_500_000, 1_200_000, 1_800_000, 2_100_000, 1_600_000],
    })


@pytest.fixture
def sample_ticker_list_df():
    return pd.DataFrame({
        'ticker':      ['2330', '2454', '6505'],
        'name':        ['台積電', '聯發科', '台塑化'],
        'market':      ['TWSE', 'TWSE', 'TWSE'],
        'listed_date': ['1994-09-05', '2001-07-23', '2003-10-10'],
    })


@pytest.fixture
def sample_fundamentals_df():
    return pd.DataFrame({
        'ticker':     ['2330'] * 3,
        'date':       ['2023-01-03', '2023-01-04', '2023-01-05'],
        'pe_ratio':   [15.2, 15.5, 14.8],
        'pb_ratio':   [5.1, 5.2, 5.0],
        'market_cap': [12_000_000_000.0] * 3,
    })
