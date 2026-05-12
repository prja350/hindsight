from __future__ import annotations
import plotly.graph_objects as go
import pandas as pd
from backtest.models import BacktestResult, Trade


def portfolio_line_chart(results: list[BacktestResult]) -> go.Figure:
    fig = go.Figure()
    for r in results:
        if not r.daily_snapshots:
            continue
        dates  = [s[0] for s in r.daily_snapshots]
        values = [s[1] for s in r.daily_snapshots]
        fig.add_trace(go.Scatter(
            x=dates, y=values, mode='lines', name=r.strategy_name,
            hovertemplate='%{x}<br>淨值: $%{y:,.0f}<extra></extra>',
        ))
    fig.update_layout(xaxis_title='日期', yaxis_title='倉位淨值（元）',
                      hovermode='x unified', margin=dict(l=40, r=20, t=30, b=40))
    return fig


def candlestick_chart(ohlcv_df: pd.DataFrame, trades: list[Trade]) -> go.Figure:
    fig = go.Figure(data=[go.Candlestick(
        x=ohlcv_df['date'] if not ohlcv_df.empty else [],
        open=ohlcv_df['open'] if not ohlcv_df.empty else [],
        high=ohlcv_df['high'] if not ohlcv_df.empty else [],
        low=ohlcv_df['low']   if not ohlcv_df.empty else [],
        close=ohlcv_df['close'] if not ohlcv_df.empty else [],
        name='K線',
        increasing_line_color='#ef4444',
        decreasing_line_color='#22c55e',
    )])
    for t in trades:
        is_buy = t.action == 'BUY'
        fig.add_annotation(
            x=t.date.isoformat(), y=t.price,
            text='▲' if is_buy else '▼', showarrow=True, arrowhead=2,
            arrowcolor='#10b981' if is_buy else '#ef4444',
            font=dict(color='#10b981' if is_buy else '#ef4444', size=14),
            yshift=10 if is_buy else -10,
        )
    fig.update_layout(xaxis_rangeslider_visible=False,
                      margin=dict(l=40, r=20, t=30, b=40))
    return fig


def stock_overlay_chart(ohlcv_map: dict[str, pd.DataFrame]) -> go.Figure:
    fig = go.Figure()
    for ticker, df in ohlcv_map.items():
        if df.empty:
            continue
        base = df['close'].iloc[0]
        fig.add_trace(go.Scatter(
            x=df['date'], y=df['close'] / base, mode='lines', name=ticker,
            hovertemplate=f'{ticker}<br>%{{x}}<br>%{{y:.3f}}x<extra></extra>',
        ))
    fig.update_layout(yaxis_title='標準化報酬 (1.0 = 起始)',
                      hovermode='x unified', margin=dict(l=40, r=20, t=30, b=40))
    return fig
