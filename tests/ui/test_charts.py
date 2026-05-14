from __future__ import annotations
from datetime import date
import pandas as pd
from backtest.models import DailySnapshot, Trade


def test_portfolio_3line_chart_has_three_traces():
    from ui.components.charts import portfolio_3line_chart
    snaps = [DailySnapshot(date(2025, 1, 2), 100, 50),
             DailySnapshot(date(2025, 1, 3), 90, 70)]
    fig = portfolio_3line_chart(snaps)
    assert len(fig.data) == 3
    names = [t.name for t in fig.data]
    assert '現金' in names and '部位市值' in names and '總資產' in names


def test_normalized_price_chart_starts_at_one():
    from ui.components.charts import normalized_price_chart
    df = pd.DataFrame([
        {'date': '2025-01-02', 'close': 100},
        {'date': '2025-01-03', 'close': 110},
    ])
    fig = normalized_price_chart({'2330': df})
    trace = fig.data[0]
    assert abs(trace.y[0] - 1.0) < 1e-9
    assert abs(trace.y[1] - 1.1) < 1e-9


def test_candlestick_chart_with_invested_overlay():
    from ui.components.charts import candlestick_chart
    ohlcv = pd.DataFrame([
        {'date': '2025-01-02', 'open': 100, 'high': 105, 'low': 95, 'close': 100,
         'quality_flag': 'clean'},
        {'date': '2025-01-03', 'open': 100, 'high': 105, 'low': 95, 'close': 100,
         'quality_flag': 'forward_filled'},
    ])
    trades = [Trade(ticker='2330', action='BUY', date=date(2025, 1, 2),
                    price=100, shares=10, amount=1000, fee=2, tax=0)]
    fig = candlestick_chart(ohlcv, trades)
    assert any(t.type == 'candlestick' for t in fig.data)
    assert any(getattr(t, 'mode', None) == 'lines' and t.name == '累計投入'
               for t in fig.data)
