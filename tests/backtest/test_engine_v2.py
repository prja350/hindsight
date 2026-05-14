from __future__ import annotations
from datetime import date
import pandas as pd
from unittest.mock import MagicMock
from backtest.engine import BacktestEngine
from backtest.models import TickerAssignment


def _provider(df_map):
    p = MagicMock()
    p.get_ohlcv.side_effect = lambda t, s, e: df_map.get(t)
    return p


def test_run_returns_v2_backtest_result_shape():
    df = pd.DataFrame([
        {'date': '2025-01-02', 'open': 100, 'high': 100, 'low': 100, 'close': 100,
         'volume': 1000, 'quality_flag': 'clean'},
        {'date': '2025-01-03', 'open': 105, 'high': 105, 'low': 105, 'close': 105,
         'volume': 1000, 'quality_flag': 'clean'},
    ])
    eng = BacktestEngine(_provider({'2330': df}))
    r = eng.run(
        assignments=[TickerAssignment('2330', 'dip_and_take_profit',
                                       {'dip_pct': 0.05, 'take_profit_pct': 0.05,
                                        'add_amount': 10000, 'max_position': 100000,
                                        'max_hold_days': 60})],
        start=date(2025, 1, 1), end=date(2025, 1, 31),
        initial_capital=500_000, execution_price='close',
    )
    assert r.initial_capital == 500_000
    assert r.execution_price == 'close'
    assert len(r.ticker_results) == 1
    assert r.ticker_results[0].ticker == '2330'
    assert len(r.daily_snapshots) >= 1
    assert all(hasattr(s, 'cash') and hasattr(s, 'position_value') for s in r.daily_snapshots)


def test_shared_capital_blocks_overspending():
    df = pd.DataFrame([
        {'date': '2025-01-02', 'open': 100, 'high': 100, 'low': 100, 'close': 100,
         'volume': 1000, 'quality_flag': 'clean'},
    ])
    eng = BacktestEngine(_provider({'2330': df, '2317': df}))
    common = {'dip_pct': 0.05, 'take_profit_pct': 0.05, 'add_amount': 6000,
              'max_position': 100000, 'max_hold_days': 60}
    r = eng.run(
        assignments=[
            TickerAssignment('2330', 'dip_and_take_profit', common),
            TickerAssignment('2317', 'dip_and_take_profit', common),
        ],
        start=date(2025, 1, 1), end=date(2025, 1, 31),
        initial_capital=10_000, execution_price='close',
    )
    buys = [t for tr in r.ticker_results for t in tr.trades if t.action == 'BUY']
    assert len(buys) == 1


def test_execution_price_open_used_for_settlement():
    df = pd.DataFrame([
        {'date': '2025-01-02', 'open': 90, 'high': 100, 'low': 85, 'close': 95,
         'volume': 1000, 'quality_flag': 'clean'},
    ])
    eng = BacktestEngine(_provider({'2330': df}))
    r = eng.run(
        assignments=[TickerAssignment('2330', 'dip_and_take_profit',
                                       {'dip_pct': 0.05, 'take_profit_pct': 0.05,
                                        'add_amount': 9_000, 'max_position': 100_000,
                                        'max_hold_days': 60})],
        start=date(2025, 1, 1), end=date(2025, 1, 31),
        initial_capital=500_000, execution_price='open',
    )
    assert r.ticker_results[0].trades[0].price == 90


def test_infinite_average_reentry():
    df = pd.DataFrame([
        {'date': '2025-01-02', 'open': 100, 'high': 100, 'low': 100, 'close': 100,
         'volume': 1000, 'quality_flag': 'clean'},
        {'date': '2025-01-03', 'open': 200, 'high': 200, 'low': 200, 'close': 200,
         'volume': 1000, 'quality_flag': 'clean'},
        {'date': '2025-01-06', 'open': 95, 'high': 95, 'low': 95, 'close': 95,
         'volume': 1000, 'quality_flag': 'clean'},
    ])
    eng = BacktestEngine(_provider({'2330': df}))
    r = eng.run(
        assignments=[TickerAssignment('2330', 'infinite_average_v0',
                                       {'dip_pct': 0.05, 'take_profit_pct': 0.05,
                                        'add_amount': 5_000, 'max_position': 100_000})],
        start=date(2025, 1, 1), end=date(2025, 1, 31),
        initial_capital=500_000, execution_price='close',
    )
    actions = [t.action for t in r.ticker_results[0].trades]
    assert actions[0] == 'BUY'
    assert 'SELL' in actions
    assert actions.count('BUY') >= 2
