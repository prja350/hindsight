from datetime import date
from backtest.models import Action, Position, Trade, Metrics, BacktestResult


def test_action_buy():
    a = Action(type="BUY", amount=10_000.0)
    assert a.type == "BUY"
    assert a.amount == 10_000.0


def test_action_defaults():
    a = Action(type="HOLD")
    assert a.amount == 0.0


def test_position_fields():
    p = Position(
        ticker="2330", shares=200, avg_cost=500.0,
        entry_date=date(2023, 1, 3), total_invested=100_000.0,
    )
    assert p.ticker == "2330"
    assert p.shares == 200


def test_trade_sell_has_realized_pnl():
    t = Trade(
        ticker="2330", action="SELL", date=date(2023, 5, 1),
        price=600.0, shares=200, amount=120_000.0,
        fee=171.0, tax=360.0, realized_pnl=19_469.0, hold_days=118,
    )
    assert t.realized_pnl == 19_469.0
    assert t.hold_days == 118


def test_metrics_fields():
    m = Metrics(
        realized_pnl=42_300.0, realized_pnl_pct=0.085,
        unrealized_pnl=3_200.0, final_cost=500_000.0, final_nav=545_500.0,
        max_drawdown=0.123, sharpe_ratio=1.42,
        win_rate=0.63, profit_factor=1.8, avg_hold_days=14.0,
    )
    assert m.sharpe_ratio == 1.42
