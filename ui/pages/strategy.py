from __future__ import annotations
from datetime import timedelta
from urllib.parse import unquote
import dash
import pandas as pd
from dash import html, dash_table, dcc

from ui.components.charts import stock_overlay_chart
from ui.state import _results

dash.register_page(__name__, path_template='/strategy/<strategy_id>')


def layout(strategy_id: str = '') -> html.Div:
    strategy_id = unquote(strategy_id)
    result = next((r for r in _results if r.strategy_name == strategy_id), None)
    if result is None:
        return html.Div(f"找不到策略：{strategy_id}", style={'padding': '40px'})

    tickers = list({t.ticker for t in result.trades})
    rows = []
    for ticker in tickers:
        ticker_trades = [t for t in result.trades if t.ticker == ticker]
        sells = [t for t in ticker_trades if t.realized_pnl is not None]
        realized = sum(t.realized_pnl for t in sells)  # type: ignore[misc]
        wr = (sum(1 for t in sells if t.realized_pnl > 0) / len(sells)  # type: ignore[operator]
              if sells else 0.0)
        rows.append({
            'ticker':       f"[{ticker}](/stock/{strategy_id}/{ticker})",
            'trade_count':  len(sells),
            'realized_pnl': f"${realized:+,.0f}",
            'win_rate':     f"{wr:.0%}",
        })

    columns = [
        {'name': '標的',      'id': 'ticker', 'presentation': 'markdown'},
        {'name': '交易次數',   'id': 'trade_count'},
        {'name': '已實現損益', 'id': 'realized_pnl'},
        {'name': 'Win Rate',  'id': 'win_rate'},
    ]

    ohlcv_map: dict[str, pd.DataFrame] = {}
    if result.daily_snapshots:
        from data.provider import DataProvider
        start = result.daily_snapshots[0][0] - timedelta(days=14)
        end = result.daily_snapshots[-1][0] + timedelta(days=14)
        provider = DataProvider()
        for ticker in tickers:
            df = provider.get_ohlcv(ticker, start, end)
            if df is not None and not df.empty:
                ohlcv_map[ticker] = df

    return html.Div([
        html.A('← 返回主頁', href='/',
               style={'fontSize': '13px', 'opacity': '.6'}),
        html.H2(f'策略：{strategy_id}', style={'margin': '12px 0 20px'}),
        dcc.Graph(figure=stock_overlay_chart(ohlcv_map), style={'marginBottom': '24px'}),
        html.H3('各標的表現',
                style={'fontSize': '14px', 'opacity': '.7', 'marginBottom': '8px'}),
        dash_table.DataTable(
            data=rows, columns=columns,
            style_cell={'textAlign': 'left', 'padding': '8px 12px', 'fontSize': '13px'},
            style_header={'fontWeight': '600', 'opacity': '.6', 'fontSize': '11px'},
        ),
        html.P('點擊標的查看 K 線與交易記錄',
               style={'fontSize': '11px', 'opacity': '.4', 'marginTop': '8px'}),
    ], style={'padding': '24px 0'})
