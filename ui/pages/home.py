from __future__ import annotations
from datetime import date
import dash
from dash import html, dash_table, dcc, callback, Input, Output, State, no_update

from ui.components.charts import portfolio_line_chart
from ui.components.tables import strategy_metrics_rows
from ui.state import _results, set_results

dash.register_page(__name__, path='/')

_INPUT = {
    'border': '1px solid #ddd', 'borderRadius': '4px',
    'padding': '6px 10px', 'fontSize': '13px', 'width': '100%',
    'boxSizing': 'border-box',
}
_LABEL = {'fontSize': '12px', 'color': '#666', 'marginBottom': '4px', 'display': 'block'}
_COL = {'flex': '1', 'marginRight': '12px'}


def _render_results() -> html.Div:
    if not _results:
        return html.Div(
            "尚無回測結果，請填寫上方表單後點擊「執行回測」。",
            style={'color': '#999', 'padding': '20px 0', 'fontSize': '14px'},
        )
    columns = [
        {'name': '策略',            'id': 'strategy'},
        {'name': '已實現損益',       'id': 'realized_pnl'},
        {'name': '未實現損益',       'id': 'unrealized_pnl'},
        {'name': '最終淨值',         'id': 'final_nav'},
        {'name': 'MDD',             'id': 'mdd'},
        {'name': 'Sharpe',          'id': 'sharpe'},
        {'name': 'Win Rate',        'id': 'win_rate'},
        {'name': 'Profit Factor',   'id': 'profit_factor'},
        {'name': 'Avg Hold (days)', 'id': 'avg_hold_days'},
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
    ])


def layout() -> html.Div:
    return html.Div([
        # ── Form ─────────────────────────────────────────────────────────────
        html.Div([
            html.H2('回測設定', style={'marginBottom': '16px', 'fontSize': '16px',
                                       'fontWeight': '600'}),
            # Row 1: tickers + date range
            html.Div([
                html.Div([
                    html.Label('股票代號（逗號分隔）', style=_LABEL),
                    dcc.Input(id='tickers-input', type='text', value='2330',
                              placeholder='2330, 2317, 0050', debounce=False,
                              style=_INPUT),
                ], style={**_COL, 'flex': '2'}),
                html.Div([
                    html.Label('起始日期', style=_LABEL),
                    dcc.Input(id='start-date', type='date', value='2022-01-01',
                              style=_INPUT),
                ], style=_COL),
                html.Div([
                    html.Label('結束日期', style=_LABEL),
                    dcc.Input(id='end-date', type='date', value='2023-12-31',
                              style={**_INPUT, 'marginRight': '0'}),
                ], style={**_COL, 'marginRight': '0'}),
            ], style={'display': 'flex', 'marginBottom': '12px'}),

            # Row 2: strategy params
            html.Div([
                html.Div([
                    html.Label('逢跌加碼幅度（%）', style=_LABEL),
                    dcc.Input(id='dip-pct', type='number', value=7,
                              min=1, max=50, step=0.5, style=_INPUT),
                ], style=_COL),
                html.Div([
                    html.Label('止盈幅度（%）', style=_LABEL),
                    dcc.Input(id='tp-pct', type='number', value=3,
                              min=0.5, max=50, step=0.5, style=_INPUT),
                ], style=_COL),
                html.Div([
                    html.Label('單次加碼金額（元）', style=_LABEL),
                    dcc.Input(id='add-amount', type='number', value=10000,
                              min=1000, step=1000, style=_INPUT),
                ], style=_COL),
                html.Div([
                    html.Label('最大持倉上限（元）', style=_LABEL),
                    dcc.Input(id='max-pos', type='number', value=100000,
                              min=10000, step=10000, style=_INPUT),
                ], style=_COL),
                html.Div([
                    html.Label('最長持有天數', style=_LABEL),
                    dcc.Input(id='max-hold', type='number', value=60,
                              min=1, max=365, step=1,
                              style={**_INPUT, 'marginRight': '0'}),
                ], style={**_COL, 'marginRight': '0'}),
            ], style={'display': 'flex', 'marginBottom': '16px'}),

            # Execute button + error message
            html.Div([
                html.Button('執行回測', id='run-btn', n_clicks=0, style={
                    'backgroundColor': '#1a73e8', 'color': '#fff',
                    'border': 'none', 'borderRadius': '4px',
                    'padding': '8px 24px', 'fontSize': '14px',
                    'cursor': 'pointer', 'fontWeight': '500',
                }),
                html.Span(id='run-error',
                          style={'marginLeft': '16px', 'color': '#c62828', 'fontSize': '13px'}),
            ]),
        ], style={
            'background': '#f8f9fa', 'border': '1px solid #e0e0e0',
            'borderRadius': '8px', 'padding': '20px', 'marginBottom': '28px',
        }),

        # ── Results ───────────────────────────────────────────────────────────
        dcc.Loading(
            type='circle',
            children=html.Div(id='home-content', children=_render_results()),
        ),
    ])


@callback(
    Output('home-content', 'children'),
    Output('run-error', 'children'),
    Input('run-btn', 'n_clicks'),
    State('tickers-input', 'value'),
    State('start-date', 'value'),
    State('end-date', 'value'),
    State('dip-pct', 'value'),
    State('tp-pct', 'value'),
    State('add-amount', 'value'),
    State('max-pos', 'value'),
    State('max-hold', 'value'),
    prevent_initial_call=True,
)
def _run_backtest(n_clicks, tickers_str, start, end,
                  dip_pct, tp_pct, add_amount, max_pos, max_hold):
    from data.provider import DataProvider
    from strategy.dip_and_take_profit import DipAndTakeProfitStrategy
    from backtest.engine import BacktestEngine

    if not tickers_str:
        return no_update, "請輸入股票代號"

    tickers = [t.strip() for t in str(tickers_str).replace('，', ',').split(',') if t.strip()]
    if not tickers:
        return no_update, "股票代號格式錯誤"

    try:
        start_d = date.fromisoformat(start)
        end_d = date.fromisoformat(end)
    except (TypeError, ValueError):
        return no_update, "日期格式錯誤（請用 YYYY-MM-DD）"

    if start_d >= end_d:
        return no_update, "起始日期必須早於結束日期"

    try:
        provider = DataProvider()
        strategy = DipAndTakeProfitStrategy(
            dip_pct=(dip_pct or 7) / 100,
            take_profit_pct=(tp_pct or 3) / 100,
            add_amount=float(add_amount or 10_000),
            max_position=float(max_pos or 100_000),
            max_hold_days=int(max_hold or 60),
        )
        engine = BacktestEngine(provider)
        result = engine.run(strategy, tickers, start_d, end_d, strategy_name="逢跌加碼止盈")
        set_results([result])
        return _render_results(), ""
    except Exception as exc:
        return no_update, f"回測失敗：{exc}"
