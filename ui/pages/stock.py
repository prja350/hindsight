from __future__ import annotations
from datetime import timedelta
from urllib.parse import unquote
import pandas as pd
import dash
from dash import html, dash_table, dcc

from ui.components.charts import candlestick_chart
from ui.components.tables import trades_table_rows
from ui.state import _results

dash.register_page(__name__, path_template='/stock/<strategy_id>/<ticker>')


def layout(strategy_id: str = '', ticker: str = '') -> html.Div:
    strategy_id = unquote(strategy_id)
    ticker = unquote(ticker)
    result = next((r for r in _results if r.strategy_name == strategy_id), None)
    if result is None:
        return html.Div(f"找不到策略：{strategy_id}", style={'padding': '40px'})

    ticker_trades = [t for t in result.trades if t.ticker == ticker]
    if not ticker_trades:
        return html.Div(f"找不到標的交易記錄：{ticker}", style={'padding': '40px'})

    ohlcv_df = pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close'])
    if result.daily_snapshots:
        from data.provider import DataProvider
        start = result.daily_snapshots[0][0] - timedelta(days=14)
        end = result.daily_snapshots[-1][0] + timedelta(days=14)
        df = DataProvider().get_ohlcv(ticker, start, end)
        if df is not None and not df.empty:
            ohlcv_df = df

    columns = [
        {'name': '日期',       'id': 'date'},
        {'name': '動作',       'id': 'action'},
        {'name': '股數',       'id': 'shares'},
        {'name': '成交價',     'id': 'price'},
        {'name': '成交金額',   'id': 'amount'},
        {'name': '手續費+稅',  'id': 'fee_tax'},
        {'name': '已實現損益', 'id': 'realized_pnl'},
    ]
    return html.Div([
        html.A(f'← 返回策略 {strategy_id}', href=f'/strategy/{strategy_id}',
               style={'fontSize': '13px', 'opacity': '.6'}),
        html.H2(f'{ticker} — {strategy_id}', style={'margin': '12px 0 20px'}),
        dcc.Graph(
            figure=candlestick_chart(ohlcv_df, ticker_trades),
            style={'marginBottom': '24px'},
        ),
        html.H3('逐筆交易記錄',
                style={'fontSize': '14px', 'opacity': '.7', 'marginBottom': '8px'}),
        dash_table.DataTable(
            data=trades_table_rows(ticker_trades),
            columns=columns,
            style_cell={'textAlign': 'left', 'padding': '8px 12px', 'fontSize': '13px'},
            style_header={'fontWeight': '600', 'opacity': '.6', 'fontSize': '11px'},
        ),
    ], style={'padding': '24px 0'})
