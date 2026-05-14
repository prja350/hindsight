from __future__ import annotations
from datetime import date
from backtest.models import (
    TickerAssignment, TickerState, PriceContext, DailySnapshot,
    TickerResult, BacktestResult, Position, Trade, Metrics, Action,
)


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


def test_metrics_fields():
    m = Metrics(
        realized_pnl=42_300.0, realized_pnl_pct=0.085,
        unrealized_pnl=3_200.0, final_cost=500_000.0, final_nav=545_500.0,
        max_drawdown=0.123, sharpe_ratio=1.42,
        win_rate=0.63, profit_factor=1.8, avg_hold_days=14.0,
    )
    assert m.sharpe_ratio == 1.42


def test_ticker_assignment_holds_class_and_params():
    a = TickerAssignment(ticker='2330', strategy_class='infinite_average_v0',
                          params={'dip_pct': 0.05})
    assert a.ticker == '2330'
    assert a.params['dip_pct'] == 0.05


def test_ticker_state_initially_empty():
    s = TickerState()
    assert s.position is None
    assert s.last_sell_price is None


def test_price_context_holds_all_prices():
    ctx = PriceContext(date(2025, 1, 2), 100, 105, 102, 102, 'clean')
    assert ctx.price == 102
    assert ctx.quality_flag == 'clean'


def test_daily_snapshot_total_property():
    s = DailySnapshot(date(2025, 1, 2), cash=10000, position_value=5000)
    assert s.total == 15000


def test_ticker_result_defaults():
    r = TickerResult(ticker='2330', strategy_class='dip_and_take_profit', params={})
    assert r.trades == []
    assert r.metrics is None


def test_backtest_result_v2_shape():
    r = BacktestResult(
        initial_capital=500_000, execution_price='close',
        start=date(2025, 1, 1), end=date(2025, 12, 31),
    )
    assert r.execution_price == 'close'
    assert r.ticker_results == []
    assert r.daily_snapshots == []
    assert r.final_cash == 0.0
