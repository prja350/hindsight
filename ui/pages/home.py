from __future__ import annotations
from datetime import date
import dash
from dash import html, dash_table, dcc, callback, Input, Output, State, no_update

from ui.components.charts import portfolio_line_chart
from ui.components.tables import strategy_metrics_rows
from ui.state import _results, set_results

dash.register_page(__name__, path='/')

# ── shared styles ─────────────────────────────────────────────────────────────
_INPUT = {
    'border': '1px solid #ddd', 'borderRadius': '4px',
    'padding': '6px 10px', 'fontSize': '13px', 'width': '100%',
    'boxSizing': 'border-box',
}
_LABEL = {'fontSize': '12px', 'color': '#666', 'marginBottom': '4px', 'display': 'block'}
_COL   = {'flex': '1', 'marginRight': '12px'}
_CARD  = {
    'background': '#f8f9fa', 'border': '1px solid #e0e0e0',
    'borderRadius': '8px', 'padding': '20px', 'marginBottom': '16px',
}


def _card(step: int, title: str, children: list) -> html.Div:
    return html.Div([
        html.Div([
            html.Span(f"Step {step}", style={
                'background': '#1a73e8', 'color': '#fff', 'fontSize': '11px',
                'fontWeight': '600', 'padding': '2px 8px', 'borderRadius': '10px',
                'marginRight': '8px',
            }),
            html.Span(title, style={'fontSize': '14px', 'fontWeight': '600', 'color': '#333'}),
        ], style={'marginBottom': '16px'}),
        *children,
    ], style=_CARD)


def _render_results() -> html.Div:
    if not _results:
        return html.Div(
            "尚無回測結果，請完成上方設定後點擊「執行回測」。",
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
        html.H2('回測結果', style={'marginBottom': '16px', 'fontSize': '18px'}),
        dcc.Graph(figure=portfolio_line_chart(_results), style={'marginBottom': '24px'}),
        html.H3('策略績效指標',
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

        # ── Step 1: Mode ─────────────────────────────────────────────────────
        _card(1, '選擇模式', [
            dcc.RadioItems(
                id='mode-radio',
                options=[
                    {'label': html.Span('個股（手動指定）',
                                        style={'marginLeft': '6px', 'marginRight': '28px'}),
                     'value': 'manual'},
                    {'label': html.Span('全隨機（從全市場隨機抽選）',
                                        style={'marginLeft': '6px', 'marginRight': '28px'}),
                     'value': 'random'},
                    {'label': html.Span('半隨機（依市場別篩選後隨機抽選）',
                                        style={'marginLeft': '6px'}),
                     'value': 'semi'},
                ],
                value='manual',
                inline=True,
                inputStyle={'cursor': 'pointer'},
                labelStyle={'cursor': 'pointer', 'fontSize': '13px'},
            ),
        ]),

        # ── Step 2: Stock config ──────────────────────────────────────────────
        _card(2, '標的設定', [

            # Date range (all modes)
            html.Div([
                html.Div([
                    html.Label('起始日期', style=_LABEL),
                    dcc.Input(id='start-date', type='date', value='2022-01-01', style=_INPUT),
                ], style=_COL),
                html.Div([
                    html.Label('結束日期', style=_LABEL),
                    dcc.Input(id='end-date', type='date', value='2023-12-31',
                              style={**_INPUT, 'marginRight': '0'}),
                ], style={**_COL, 'marginRight': '0'}),
            ], style={'display': 'flex', 'marginBottom': '14px'}),

            # Manual: ticker list
            html.Div([
                html.Label('股票代號（逗號分隔）', style=_LABEL),
                dcc.Input(id='tickers-input', type='text', value='2330',
                          placeholder='2330, 2317, 0050', style=_INPUT),
            ], id='sec-manual', style={'marginBottom': '4px'}),

            # Random/Semi: n stocks
            html.Div([
                html.Label('隨機選取檔數', style=_LABEL),
                dcc.Input(id='n-stocks', type='number', value=5, min=1, max=100, step=1,
                          style={**_INPUT, 'width': '120px'}),
            ], id='sec-n', style={'display': 'none', 'marginBottom': '4px'}),

            # Semi: market filter
            html.Div([
                html.Label('市場別', style={**_LABEL, 'marginTop': '10px'}),
                dcc.RadioItems(
                    id='market-radio',
                    options=[
                        {'label': html.Span('全部', style={'marginLeft': '5px', 'marginRight': '20px'}),
                         'value': 'all'},
                        {'label': html.Span('上市（TWSE）', style={'marginLeft': '5px', 'marginRight': '20px'}),
                         'value': 'TWSE'},
                        {'label': html.Span('上櫃（TPEx）', style={'marginLeft': '5px'}),
                         'value': 'TPEx'},
                    ],
                    value='all',
                    inline=True,
                    inputStyle={'cursor': 'pointer'},
                    labelStyle={'cursor': 'pointer', 'fontSize': '13px'},
                ),
            ], id='sec-market', style={'display': 'none'}),

        ]),

        # ── Step 3: Strategy ──────────────────────────────────────────────────
        _card(3, '選擇策略', [
            html.Div([
                html.Span('逢跌加碼止盈', style={
                    'fontSize': '13px', 'fontWeight': '600',
                    'display': 'block', 'marginBottom': '12px',
                }),
                html.Div([
                    html.Div([
                        html.Label('逢跌幅度（%）', style=_LABEL),
                        dcc.Input(id='dip-pct', type='number', value=7,
                                  min=1, max=50, step=0.5, style=_INPUT),
                    ], style=_COL),
                    html.Div([
                        html.Label('止盈幅度（%）', style=_LABEL),
                        dcc.Input(id='tp-pct', type='number', value=3,
                                  min=0.5, max=50, step=0.5, style=_INPUT),
                    ], style=_COL),
                    html.Div([
                        html.Label('單次加碼（元）', style=_LABEL),
                        dcc.Input(id='add-amount', type='number', value=10000,
                                  min=1000, step=1000, style=_INPUT),
                    ], style=_COL),
                    html.Div([
                        html.Label('持倉上限（元）', style=_LABEL),
                        dcc.Input(id='max-pos', type='number', value=100000,
                                  min=10000, step=10000, style=_INPUT),
                    ], style=_COL),
                    html.Div([
                        html.Label('最長持有天數', style=_LABEL),
                        dcc.Input(id='max-hold', type='number', value=60,
                                  min=1, step=1,
                                  style={**_INPUT, 'marginRight': '0'}),
                    ], style={**_COL, 'marginRight': '0'}),
                ], style={'display': 'flex'}),
            ], style={
                'border': '1px solid #e0e0e0', 'borderRadius': '6px',
                'padding': '14px', 'background': '#fff',
            }),
        ]),

        # ── Execute ───────────────────────────────────────────────────────────
        html.Div([
            html.Button('執行回測', id='run-btn', n_clicks=0, style={
                'backgroundColor': '#1a73e8', 'color': '#fff', 'border': 'none',
                'borderRadius': '4px', 'padding': '10px 32px', 'fontSize': '14px',
                'cursor': 'pointer', 'fontWeight': '500',
            }),
            html.Span(id='run-error',
                      style={'marginLeft': '16px', 'color': '#c62828', 'fontSize': '13px'}),
        ], style={'marginBottom': '28px'}),

        # ── Results ───────────────────────────────────────────────────────────
        dcc.Loading(
            type='circle',
            children=html.Div(id='home-content', children=_render_results()),
        ),
    ])


# ── Callback: toggle mode sections ───────────────────────────────────────────

@callback(
    Output('sec-manual', 'style'),
    Output('sec-n', 'style'),
    Output('sec-market', 'style'),
    Input('mode-radio', 'value'),
)
def _toggle_sections(mode: str):
    show_manual  = {'marginBottom': '4px'}
    show_n       = {'marginBottom': '4px'}
    show_market  = {}
    hide         = {'display': 'none'}

    if mode == 'manual':
        return show_manual, hide, hide
    elif mode == 'random':
        return hide, show_n, hide
    else:  # semi
        return hide, show_n, show_market


# ── Callback: run backtest ────────────────────────────────────────────────────

@callback(
    Output('home-content', 'children'),
    Output('run-error', 'children'),
    Input('run-btn', 'n_clicks'),
    State('mode-radio', 'value'),
    State('tickers-input', 'value'),
    State('start-date', 'value'),
    State('end-date', 'value'),
    State('n-stocks', 'value'),
    State('market-radio', 'value'),
    State('dip-pct', 'value'),
    State('tp-pct', 'value'),
    State('add-amount', 'value'),
    State('max-pos', 'value'),
    State('max-hold', 'value'),
    prevent_initial_call=True,
)
def _run_backtest(n_clicks, mode, tickers_str, start, end, n_stocks, market,
                  dip_pct, tp_pct, add_amount, max_pos, max_hold):
    from data.provider import DataProvider
    from selection.manual import ManualSelector
    from selection.random_mode import RandomSelector
    from selection.semi_random import SemiRandomSelector
    from strategy.dip_and_take_profit import DipAndTakeProfitStrategy
    from backtest.engine import BacktestEngine

    try:
        start_d = date.fromisoformat(start)
        end_d = date.fromisoformat(end)
    except (TypeError, ValueError):
        return no_update, "日期格式錯誤（請用 YYYY-MM-DD）"

    if start_d >= end_d:
        return no_update, "起始日期必須早於結束日期"

    try:
        provider = DataProvider()

        if mode == 'manual':
            if not tickers_str:
                return no_update, "請輸入股票代號"
            tickers = [t.strip() for t in str(tickers_str).replace('，', ',').split(',')
                       if t.strip()]
            if not tickers:
                return no_update, "股票代號格式錯誤"
            sel = ManualSelector(tickers, start_d, end_d, provider).select()

        elif mode == 'random':
            n = int(n_stocks or 5)
            sel = RandomSelector(n, provider, start=start_d, end=end_d).select()
            if not sel.tickers:
                return no_update, "無法取得股票清單，請確認 FinMind token 或網路連線"

        else:  # semi
            n = int(n_stocks or 5)
            ticker_df = provider.get_ticker_list()
            if ticker_df is None or ticker_df.empty:
                return no_update, "無法取得股票清單，請確認 FinMind token 或網路連線"
            if market and market != 'all':
                ticker_df = ticker_df[ticker_df['market'] == market]
            if ticker_df.empty:
                return no_update, f"市場別「{market}」無符合標的"
            sel = SemiRandomSelector(n, start_d, end_d, [], provider).select()
            # Override tickers with market-filtered pool
            import random as _rnd
            pool = ticker_df['ticker'].tolist()
            sel_tickers = _rnd.sample(pool, min(n, len(pool)))
            from selection.manual import SelectionResult
            sel = SelectionResult(tickers=sel_tickers, start=start_d, end=end_d)

        strategy = DipAndTakeProfitStrategy(
            dip_pct=(dip_pct or 7) / 100,
            take_profit_pct=(tp_pct or 3) / 100,
            add_amount=float(add_amount or 10_000),
            max_position=float(max_pos or 100_000),
            max_hold_days=int(max_hold or 60),
        )
        engine = BacktestEngine(provider)
        result = engine.run(
            strategy, sel.tickers, sel.start, sel.end,
            strategy_name="逢跌加碼止盈",
        )
        set_results([result])
        return _render_results(), ""

    except Exception as exc:
        return no_update, f"回測失敗：{exc}"
