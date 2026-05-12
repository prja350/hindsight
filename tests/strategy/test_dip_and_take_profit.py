import pytest
from datetime import date
from backtest.models import Action, Position
from strategy.dip_and_take_profit import DipAndTakeProfitStrategy


@pytest.fixture
def strategy():
    return DipAndTakeProfitStrategy(
        dip_pct=0.07, add_amount=10_000.0,
        take_profit_pct=0.03, max_position=100_000.0, max_hold_days=60,
    )


@pytest.fixture
def open_position():
    return Position(
        ticker='2330', shares=200, avg_cost=500.0,
        entry_date=date(2023, 1, 3), total_invested=50_000.0,
    )


def test_initial_buy_when_no_position(strategy):
    action = strategy.on_price_update(date(2023, 1, 3), 500.0, None)
    assert action.type == "BUY"
    assert action.amount == 10_000.0


def test_hold_when_price_stable(strategy, open_position):
    # avg_cost=500, drop=2% — below 7% dip threshold
    action = strategy.on_price_update(date(2023, 1, 4), 490.0, open_position)
    assert action.type == "HOLD"


def test_add_when_price_drops_enough(strategy, open_position):
    # 7% of 500 = 35 → trigger at ≤465
    action = strategy.on_price_update(date(2023, 1, 4), 464.0, open_position)
    assert action.type == "BUY"
    assert action.amount == 10_000.0


def test_no_add_when_max_position_reached(strategy):
    position = Position(
        ticker='2330', shares=200, avg_cost=500.0,
        entry_date=date(2023, 1, 3), total_invested=100_000.0,
    )
    # total_invested == max_position → adding 10k would exceed limit
    action = strategy.on_price_update(date(2023, 1, 4), 464.0, position)
    assert action.type == "HOLD"


def test_sell_when_take_profit_reached(strategy, open_position):
    # avg_cost=500, take_profit=3% → sell at ≥515
    action = strategy.on_price_update(date(2023, 3, 1), 516.0, open_position)
    assert action.type == "SELL"


def test_force_close_when_max_hold_days_exceeded(strategy, open_position):
    # entry=2023-01-03, max_hold_days=60 → force at day 60+
    action = strategy.on_price_update(date(2023, 3, 5), 495.0, open_position)
    assert action.type == "SELL"


def test_hold_before_max_hold_days(strategy, open_position):
    # day 58 from entry (2023-01-03 + 58 = 2023-03-02)
    action = strategy.on_price_update(date(2023, 3, 2), 495.0, open_position)
    assert action.type == "HOLD"
