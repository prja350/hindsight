from __future__ import annotations
from datetime import date
import pandas as pd
from unittest.mock import MagicMock
from backtest.engine import BacktestEngine
from backtest.models import TickerAssignment


def test_two_tickers_two_strategies():
    df_a = pd.DataFrame([
        {'date': f'2026-01-0{d}', 'open': 100 + d, 'high': 105 + d, 'low': 95 + d,
         'close': 100 + d, 'volume': 1000, 'quality_flag': 'clean'}
        for d in range(2, 7)
    ])
    df_b = pd.DataFrame([
        {'date': f'2026-01-0{d}', 'open': 50 + d * 2, 'high': 55 + d * 2,
         'low': 45 + d * 2, 'close': 50 + d * 2, 'volume': 1000, 'quality_flag': 'clean'}
        for d in range(2, 7)
    ])
    provider = MagicMock()
    provider.get_ohlcv.side_effect = lambda t, s, e: df_a if t == '2330' else df_b

    result = BacktestEngine(provider).run(
        assignments=[
            TickerAssignment('2330', 'dip_and_take_profit',
                {'dip_pct': 0.05, 'take_profit_pct': 0.05,
                 'add_amount': 5000, 'max_position': 50000, 'max_hold_days': 60}),
            TickerAssignment('2317', 'infinite_average_v0',
                {'dip_pct': 0.05, 'take_profit_pct': 0.05,
                 'add_amount': 5000, 'max_position': 50000}),
        ],
        start=date(2026, 1, 1), end=date(2026, 1, 31),
        initial_capital=100_000, execution_price='close',
    )
    assert len(result.ticker_results) == 2
    assert {tr.ticker for tr in result.ticker_results} == {'2330', '2317'}
    assert all(tr.metrics is not None for tr in result.ticker_results)
    assert len(result.daily_snapshots) >= 1
    assert result.daily_snapshots[0].cash <= 100_000
