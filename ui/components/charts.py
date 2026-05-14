from __future__ import annotations
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from backtest.models import DailySnapshot, Trade


def portfolio_3line_chart(snaps: list[DailySnapshot]) -> go.Figure:
    if not snaps:
        return go.Figure()
    dates = [s.date for s in snaps]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=[s.cash for s in snaps],
                             mode='lines', name='現金',
                             line=dict(color='#2e7d32', width=1.5)))
    fig.add_trace(go.Scatter(x=dates, y=[s.position_value for s in snaps],
                             mode='lines', name='部位市值',
                             line=dict(color='#1976d2', width=1.5)))
    fig.add_trace(go.Scatter(x=dates, y=[s.total for s in snaps],
                             mode='lines', name='總資產',
                             line=dict(color='#212121', width=2.5)))
    fig.update_layout(
        height=380, margin=dict(t=20, b=30, l=40, r=20),
        legend=dict(orientation='h', y=1.05),
        yaxis=dict(title='NTD', tickformat=','),
    )
    return fig


def normalized_price_chart(ohlcv_map: dict[str, pd.DataFrame]) -> go.Figure:
    fig = go.Figure()
    for ticker, df in ohlcv_map.items():
        if df is None or df.empty:
            continue
        df = df.sort_values('date').reset_index(drop=True)
        base = float(df.iloc[0]['close'])
        if base == 0:
            continue
        fig.add_trace(go.Scatter(
            x=df['date'].tolist(),
            y=(df['close'] / base).tolist(),
            mode='lines', name=ticker,
        ))
    fig.update_layout(
        height=360, margin=dict(t=20, b=30, l=40, r=20),
        yaxis=dict(title='Normalized (base=1.0)'),
        legend=dict(orientation='h', y=1.05),
    )
    return fig


def candlestick_chart(ohlcv: pd.DataFrame, trades: list[Trade]) -> go.Figure:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.7, 0.3], vertical_spacing=0.05,
                        subplot_titles=('K 線', '累計投入'))

    if ohlcv is not None and not ohlcv.empty:
        fig.add_trace(go.Candlestick(
            x=ohlcv['date'], open=ohlcv['open'], high=ohlcv['high'],
            low=ohlcv['low'], close=ohlcv['close'], name='K',
            increasing_line_color='#d32f2f', decreasing_line_color='#388e3c',
        ), row=1, col=1)

        if 'quality_flag' in ohlcv.columns:
            ff = ohlcv[ohlcv['quality_flag'] == 'forward_filled']
            for d in ff['date']:
                fig.add_vrect(x0=d, x1=d, fillcolor='#cccccc', opacity=0.3,
                              line_width=0, row=1, col=1)

    buys = [t for t in trades if t.action == 'BUY']
    sells = [t for t in trades if t.action == 'SELL']
    first_buy = buys[:1]
    add_buys = buys[1:]
    if first_buy:
        fig.add_trace(go.Scatter(
            x=[t.date for t in first_buy], y=[t.price for t in first_buy],
            mode='markers', name='買入',
            marker=dict(symbol='triangle-up', color='#1976d2', size=12),
        ), row=1, col=1)
    if add_buys:
        fig.add_trace(go.Scatter(
            x=[t.date for t in add_buys], y=[t.price for t in add_buys],
            mode='markers', name='加碼',
            marker=dict(symbol='triangle-up', color='#64b5f6', size=10,
                        line=dict(color='#1976d2', width=1)),
        ), row=1, col=1)
    if sells:
        fig.add_trace(go.Scatter(
            x=[t.date for t in sells], y=[t.price for t in sells],
            mode='markers', name='賣出',
            marker=dict(symbol='triangle-down', color='#f57c00', size=12),
        ), row=1, col=1)

    if trades and ohlcv is not None and not ohlcv.empty:
        dates_sorted = sorted({d for d in ohlcv['date'].tolist()})
        trade_by_date: dict[str, list[Trade]] = {}
        for t in trades:
            trade_by_date.setdefault(t.date.isoformat(), []).append(t)
        invested = 0.0
        series_x, series_y = [], []
        for d in dates_sorted:
            for t in trade_by_date.get(d, []):
                if t.action == 'BUY':
                    invested += t.amount + t.fee
                elif t.action == 'SELL':
                    invested = 0.0
            series_x.append(d); series_y.append(invested)
        fig.add_trace(go.Scatter(
            x=series_x, y=series_y, mode='lines', name='累計投入',
            line=dict(color='#7b1fa2', width=2),
        ), row=2, col=1)

    fig.update_layout(
        height=600, margin=dict(t=40, b=30, l=40, r=20),
        legend=dict(orientation='h', y=1.05),
        xaxis_rangeslider_visible=False,
    )
    return fig


def stock_overlay_chart(ohlcv_map: dict[str, pd.DataFrame]) -> go.Figure:
    return normalized_price_chart(ohlcv_map)


def portfolio_line_chart(results) -> go.Figure:
    if not results:
        return go.Figure()
    r = results[0] if isinstance(results, list) else results
    if hasattr(r, 'daily_snapshots'):
        return portfolio_3line_chart(r.daily_snapshots)
    return go.Figure()
