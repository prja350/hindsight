from __future__ import annotations
from datetime import timedelta
import dash
import pandas as pd
from dash import html, dash_table, dcc

from ui.components.charts import normalized_price_chart
from ui.components.tables import STRATEGY_LABEL
from ui.state import current_result

dash.register_page(__name__, path_template='/strategy/<class_name>')


def layout(class_name: str = '') -> html.Div:
    label = STRATEGY_LABEL.get(class_name, class_name)
    result = current_result()
    if result is None:
        return html.Div('尚無回測結果', style={'padding': '40px'})

    matches = [tr for tr in result.ticker_results if tr.strategy_class == class_name]
    if not matches:
        return html.Div(f'此策略類別無 ticker：{class_name}', style={'padding': '40px'})

    ohlcv_map: dict[str, pd.DataFrame] = {}
    if result.daily_snapshots:
        from data.provider import DataProvider
        s = result.daily_snapshots[0].date - timedelta(days=14)
        e = result.daily_snapshots[-1].date + timedelta(days=14)
        provider = DataProvider()
        for tr in matches:
            df = provider.get_ohlcv(tr.ticker, s, e)
            if df is not None and not df.empty:
                ohlcv_map[tr.ticker] = df

    rows = []
    for tr in matches:
        sells = [t for t in tr.trades if t.realized_pnl is not None]
        realized = sum(t.realized_pnl for t in sells)
        wr = (sum(1 for t in sells if t.realized_pnl > 0) / len(sells)) if sells else 0.0
        rows.append({
            'ticker':       f"[{tr.ticker}](/stock/{class_name}/{tr.ticker})",
            'trade_count':  len(sells),
            'realized_pnl': f"${realized:+,.0f}",
            'win_rate':     f"{wr:.0%}",
        })

    columns = [
        {'name': '標的', 'id': 'ticker', 'presentation': 'markdown'},
        {'name': '交易次數', 'id': 'trade_count'},
        {'name': '已實現損益', 'id': 'realized_pnl'},
        {'name': 'Win Rate', 'id': 'win_rate'},
    ]
    return html.Div([
        html.A('← 返回主頁', href='/', style={'fontSize': '13px', 'opacity': '.6'}),
        html.H2(f'策略類別：{label}', style={'margin': '12px 0 20px'}),
        dcc.Graph(figure=normalized_price_chart(ohlcv_map), style={'marginBottom': '24px'}),
        html.H3('各標的表現', style={'fontSize': '14px', 'opacity': '.7', 'marginBottom': '8px'}),
        dash_table.DataTable(
            data=rows, columns=columns,
            style_cell={'textAlign': 'left', 'padding': '8px 12px', 'fontSize': '13px'},
            style_header={'fontWeight': '600', 'opacity': '.6', 'fontSize': '11px'},
        ),
    ], style={'padding': '24px 0'})
