import pytest
import pandas as pd
from datetime import date
from unittest.mock import MagicMock
from backtest.engine import BacktestEngine
from backtest.models import BacktestResult
from strategy.dip_and_take_profit import DipAndTakeProfitStrategy


@pytest.fixture
def ohlcv_10d():
    dates = pd.date_range('2023-01-03', periods=10, freq='B')
    # prices: initial buy at 500, dip below 465 on day 4, recover and pass take-profit
    prices = [500, 498, 495, 464, 460, 480, 495, 510, 516, 520]
    return pd.DataFrame({
        'ticker': ['2330'] * 10,
        'date': [d.strftime('%Y-%m-%d') for d in dates],
        'open': prices, 'high': prices, 'low': prices,
        'close': prices, 'volume': [1_000_000] * 10,
    })


@pytest.fixture
def mock_provider(ohlcv_10d):
    p = MagicMock()
    p.get_ohlcv.return_value = ohlcv_10d
    return p


@pytest.fixture
def strategy():
    return DipAndTakeProfitStrategy(
        dip_pct=0.07, add_amount=10_000.0,
        take_profit_pct=0.03, max_position=100_000.0, max_hold_days=60,
    )


def test_run_returns_backtest_result(mock_provider, strategy):
    engine = BacktestEngine(provider=mock_provider, initial_capital=500_000.0)
    result = engine.run(strategy, ['2330'], date(2023, 1, 3), date(2023, 1, 16), 'test')
    assert isinstance(result, BacktestResult)
    assert result.strategy_name == 'test'


def test_run_records_buy_on_first_day(mock_provider, strategy):
    engine = BacktestEngine(provider=mock_provider, initial_capital=500_000.0)
    result = engine.run(strategy, ['2330'], date(2023, 1, 3), date(2023, 1, 16), 'test')
    buy_trades = [t for t in result.trades if t.action == 'BUY']
    assert len(buy_trades) >= 1
    assert buy_trades[0].date == date(2023, 1, 3)


def test_buy_fee_is_01425_pct(mock_provider, strategy):
    engine = BacktestEngine(provider=mock_provider, initial_capital=500_000.0)
    result = engine.run(strategy, ['2330'], date(2023, 1, 3), date(2023, 1, 16), 'test')
    for t in result.trades:
        if t.action == 'BUY':
            expected_fee = round(t.amount * 0.001425)
            assert abs(t.fee - expected_fee) <= 1


def test_run_produces_daily_snapshots(mock_provider, strategy):
    engine = BacktestEngine(provider=mock_provider, initial_capital=500_000.0)
    result = engine.run(strategy, ['2330'], date(2023, 1, 3), date(2023, 1, 16), 'test')
    assert len(result.daily_snapshots) == 10


def test_run_calculates_metrics(mock_provider, strategy):
    engine = BacktestEngine(provider=mock_provider, initial_capital=500_000.0)
    result = engine.run(strategy, ['2330'], date(2023, 1, 3), date(2023, 1, 16), 'test')
    assert result.metrics is not None
    assert 0.0 <= result.metrics.win_rate <= 1.0
