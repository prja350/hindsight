from __future__ import annotations
import dash
from dash import html, dash_table, dcc

from ui.components.charts import portfolio_line_chart
from ui.components.tables import strategy_metrics_rows

dash.register_page(__name__, path='/')

_results: list = []


def set_results(results: list) -> None:
    global _results
    _results = results


def layout() -> html.Div:
    if not _results:
        return html.Div("尚無回測結果。請先執行回測。",
                        style={'padding': '40px', 'opacity': '.6'})
    columns = [
        {'name': '策略',        'id': 'strategy'},
        {'name': '已實現損益',   'id': 'realized_pnl'},
        {'name': '未實現損益',   'id': 'unrealized_pnl'},
        {'name': '最終淨值',    'id': 'final_nav'},
        {'name': 'MDD',        'id': 'mdd'},
        {'name': 'Sharpe',     'id': 'sharpe'},
        {'name': 'Win Rate',   'id': 'win_rate'},
        {'name': 'Profit Factor', 'id': 'profit_factor'},
        {'name': 'Avg Hold',   'id': 'avg_hold_days'},
    ]
    return html.Div([
        html.H2('策略比較概覽', style={'marginBottom': '16px'}),
        dcc.Graph(figure=portfolio_line_chart(_results), style={'marginBottom': '24px'}),
        html.H3('指標比較表',
                style={'marginBottom': '8px', 'fontSize': '14px', 'opacity': '.7'}),
        dash_table.DataTable(
            data=strategy_metrics_rows(_results),
            columns=columns,
            style_cell={'textAlign': 'left', 'padding': '8px 12px', 'fontSize': '13px'},
            style_header={'fontWeight': '600', 'opacity': '.6', 'fontSize': '11px'},
        ),
    ], style={'padding': '24px 0'})
