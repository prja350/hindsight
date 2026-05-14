from __future__ import annotations
from datetime import date
from backtest.models import Position, TickerState
from strategy.pnl import net_unrealized_pct, net_unrealized_value


def test_no_position_returns_zero():
    s = TickerState(position=None)
    assert net_unrealized_pct(s, 100.0) == 0.0


def test_positive_pnl_net_of_fees():
    pos = Position('2330', shares=10, avg_cost=100, entry_date=date(2025, 1, 2),
                   total_invested=1000)
    s = TickerState(position=pos)
    pct = net_unrealized_pct(s, 110.0)
    assert abs(pct - 0.0951325) < 1e-6


def test_negative_pnl():
    pos = Position('2330', shares=10, avg_cost=100, entry_date=date(2025, 1, 2),
                   total_invested=1000)
    s = TickerState(position=pos)
    assert net_unrealized_pct(s, 90.0) < -0.1


def test_zero_invested_returns_zero():
    pos = Position('2330', shares=0, avg_cost=0, entry_date=date(2025, 1, 2),
                   total_invested=0)
    s = TickerState(position=pos)
    assert net_unrealized_pct(s, 100.0) == 0.0


def test_net_unrealized_value_no_position():
    s = TickerState(position=None)
    assert net_unrealized_value(s, 100.0) == 0.0


def test_net_unrealized_value_positive():
    pos = Position('2330', shares=10, avg_cost=100, entry_date=date(2025, 1, 2),
                   total_invested=1000)
    s = TickerState(position=pos)
    v = net_unrealized_value(s, 110.0)
    assert abs(v - 95.1325) < 1e-6
