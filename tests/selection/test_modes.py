import pytest
from datetime import date
from unittest.mock import MagicMock
from selection.manual import ManualSelector, SelectionResult
from selection.random_mode import RandomSelector
from selection.semi_random import SemiRandomSelector
from selection.filters.price import PriceFilter


@pytest.fixture
def mock_provider(sample_ticker_list_df):
    provider = MagicMock()
    provider.get_ticker_list.return_value = sample_ticker_list_df
    return provider


def test_manual_returns_requested_tickers(mock_provider):
    sel = ManualSelector(
        tickers=['2330', '2454'], start=date(2023, 1, 1),
        end=date(2023, 12, 31), provider=mock_provider,
    )
    result = sel.select()
    assert result.tickers == ['2330', '2454']
    assert result.start == date(2023, 1, 1)


def test_random_returns_n_tickers(mock_provider):
    sel = RandomSelector(n=2, provider=mock_provider)
    result = sel.select()
    assert len(result.tickers) == 2
    assert result.start < result.end


def test_random_n_capped_to_available(mock_provider):
    sel = RandomSelector(n=100, provider=mock_provider)
    result = sel.select()
    assert len(result.tickers) == 3  # only 3 in fixture


def test_random_respects_fixed_dates(mock_provider):
    sel = RandomSelector(n=2, provider=mock_provider,
                         start=date(2022, 1, 1), end=date(2022, 12, 31))
    result = sel.select()
    assert result.start == date(2022, 1, 1)
    assert result.end == date(2022, 12, 31)


def test_semi_random_applies_filters(mock_provider):
    import pandas as pd
    enriched = pd.DataFrame({
        'ticker': ['2330', '2454', '6505'], 'name': ['台積電', '聯發科', '台塑化'],
        'market': ['TWSE'] * 3, 'listed_date': ['1994-09-05', '2001-07-23', '2003-10-10'],
        'close': [580.0, 850.0, 95.0], 'volume': [20_000_000, 5_000_000, 500_000],
        'pe_ratio': [15.0, 30.0, 8.0], 'volatility': [0.25, 0.35, 0.15],
    })
    mock_provider.get_ticker_list.return_value = enriched
    sel = SemiRandomSelector(
        n=10, start=date(2023, 1, 1), end=date(2023, 12, 31),
        filters=[PriceFilter(max_price=200.0)], provider=mock_provider,
    )
    result = sel.select()
    assert result.tickers == ['6505']


def test_semi_random_returns_up_to_n(mock_provider):
    sel = SemiRandomSelector(
        n=2, start=date(2023, 1, 1), end=date(2023, 12, 31),
        filters=[], provider=mock_provider,
    )
    assert len(sel.select().tickers) <= 2
