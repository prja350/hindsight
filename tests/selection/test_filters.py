import pandas as pd
import pytest
from selection.filters.price import PriceFilter
from selection.filters.volume import VolumeFilter
from selection.filters.pe_ratio import PERatioFilter
from selection.filters.volatility import VolatilityFilter


@pytest.fixture
def stocks_df():
    return pd.DataFrame({
        'ticker':     ['2330', '2454', '6505', '2317'],
        'close':      [580.0,  850.0,  95.0,  105.0],
        'volume':     [20_000_000, 5_000_000, 500_000, 8_000_000],
        'pe_ratio':   [15.0, 30.0, 8.0, 12.0],
        'volatility': [0.25, 0.35, 0.15, 0.20],
    })


def test_price_filter_max(stocks_df):
    result = PriceFilter(max_price=200.0).apply(stocks_df)
    assert set(result['ticker']) == {'6505', '2317'}


def test_price_filter_min_and_max(stocks_df):
    result = PriceFilter(min_price=100.0, max_price=600.0).apply(stocks_df)
    assert set(result['ticker']) == {'2330', '2317'}


def test_volume_filter(stocks_df):
    result = VolumeFilter(min_volume=6_000_000).apply(stocks_df)
    assert set(result['ticker']) == {'2330', '2317'}


def test_pe_ratio_filter(stocks_df):
    result = PERatioFilter(min_pe=10.0, max_pe=20.0).apply(stocks_df)
    assert set(result['ticker']) == {'2330', '2317'}


def test_volatility_filter(stocks_df):
    result = VolatilityFilter(min_vol=0.22).apply(stocks_df)
    assert set(result['ticker']) == {'2330', '2454'}


def test_filters_chain(stocks_df):
    df = PriceFilter(max_price=200.0).apply(stocks_df)
    df = VolumeFilter(min_volume=1_000_000).apply(df)
    assert set(df['ticker']) == {'2317'}
