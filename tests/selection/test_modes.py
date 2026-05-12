import pytest
from datetime import date
from unittest.mock import MagicMock
from selection.manual import ManualSelector, SelectionResult
from selection.random_mode import RandomSelector


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
