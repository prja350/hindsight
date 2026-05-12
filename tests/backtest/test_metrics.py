import math
from datetime import date
from backtest.models import Trade
from backtest.metrics import MetricsCalculator


def _sell(pnl: float, hold_days: int = 10) -> Trade:
    return Trade(
        ticker='2330', action='SELL', date=date(2023, 3, 1),
        price=600.0, shares=100, amount=60_000.0, fee=85.0, tax=180.0,
        realized_pnl=pnl, hold_days=hold_days,
    )


SNAPS = [
    (date(2023, 1, 3), 100_000.0), (date(2023, 1, 4), 101_000.0),
    (date(2023, 1, 5),  98_000.0), (date(2023, 1, 6), 105_000.0),
    (date(2023, 1, 9), 102_000.0),
]


def test_win_rate_all_wins():
    m = MetricsCalculator([_sell(1000)] * 3, SNAPS, 100_000.0).calculate()
    assert m.win_rate == 1.0


def test_win_rate_mixed():
    m = MetricsCalculator([_sell(1000), _sell(-500), _sell(200)], SNAPS, 100_000.0).calculate()
    assert abs(m.win_rate - 2/3) < 1e-6


def test_profit_factor():
    m = MetricsCalculator([_sell(1000), _sell(-200)], SNAPS, 100_000.0).calculate()
    assert abs(m.profit_factor - 5.0) < 1e-6


def test_avg_hold_days():
    m = MetricsCalculator([_sell(100, 10), _sell(100, 20)], SNAPS, 100_000.0).calculate()
    assert m.avg_hold_days == 15.0


def test_max_drawdown():
    snaps = [
        (date(2023, 1, 3), 100_000.0), (date(2023, 1, 4), 110_000.0),
        (date(2023, 1, 5),  88_000.0), (date(2023, 1, 6), 105_000.0),
    ]
    m = MetricsCalculator([], snaps, 100_000.0).calculate()
    assert abs(m.max_drawdown - 0.2) < 1e-6


def test_sharpe_zero_for_flat_curve():
    flat = [(date(2023, 1, i+3), 100_000.0) for i in range(5)]
    m = MetricsCalculator([], flat, 100_000.0).calculate()
    assert m.sharpe_ratio == 0.0
