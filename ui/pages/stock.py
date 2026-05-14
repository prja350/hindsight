from __future__ import annotations
from datetime import timedelta
import pandas as pd
import dash
from dash import html, dash_table, dcc

from ui.components.charts import candlestick_chart
from ui.components.tables import trades_table_rows, STRATEGY_LABEL
from ui.state import current_result

dash.register_page(__name__, path_template='/stock/<class_name>/<ticker>')


def layout(class_name: str = '', ticker: str = '') -> html.Div:
    result = current_result()
    if result is None:
        return html.Div('尚無回測結果', style={'padding': '40px'})

    tr = next((x for x in result.ticker_results
               if x.strategy_class == class_name and x.ticker == ticker), None)
    if tr is None:
        return html.Div(f'找不到：{class_name} / {ticker}', style={'padding': '40px'})

    ohlcv_df = pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'quality_flag'])
    if result.daily_snapshots:
        from data.provider import DataProvider
        s = result.daily_snapshots[0].date - timedelta(days=14)
        e = result.daily_snapshots[-1].date + timedelta(days=14)
        df = DataProvider().get_ohlcv(ticker, s, e)
        if df is not None and not df.empty:
            ohlcv_df = df

    columns = [
        {'name': '日期', 'id': 'date'},
        {'name': '動作', 'id': 'action'},
        {'name': '股數', 'id': 'shares'},
        {'name': '成交價', 'id': 'price'},
        {'name': '成交金額', 'id': 'amount'},
        {'name': '手續費+稅', 'id': 'fee_tax'},
        {'name': '已實現損益', 'id': 'realized_pnl'},
        {'name': '持有天數', 'id': 'hold_days'},
    ]
    label = STRATEGY_LABEL.get(class_name, class_name)
    return html.Div([
        html.A(f'← 返回策略 {label}', href=f'/strategy/{class_name}',
               style={'fontSize': '13px', 'opacity': '.6'}),
        html.H2(f'{ticker} — {label}', style={'margin': '12px 0 20px'}),
        dcc.Graph(figure=candlestick_chart(ohlcv_df, tr.trades),
                  style={'marginBottom': '24px'}),
        html.H3('逐筆交易記錄',
                style={'fontSize': '14px', 'opacity': '.7', 'marginBottom': '8px'}),
        dash_table.DataTable(
            data=trades_table_rows(tr.trades), columns=columns,
            style_cell={'textAlign': 'left', 'padding': '8px 12px', 'fontSize': '13px'},
            style_header={'fontWeight': '600', 'opacity': '.6', 'fontSize': '11px'},
        ),
    ], style={'padding': '24px 0'})
