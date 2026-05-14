from __future__ import annotations
from datetime import date
import dash
from dash import html, dash_table, dcc, callback, Input, Output, State, ALL, MATCH, no_update

from ui.components.charts import portfolio_3line_chart
from ui.components.tables import per_ticker_rows
from ui.state import current_result, set_results

dash.register_page(__name__, path='/')

_INPUT = {'border': '1px solid #ddd', 'borderRadius': '4px', 'padding': '6px 10px',
          'fontSize': '13px', 'width': '100%', 'boxSizing': 'border-box'}
_LABEL = {'fontSize': '12px', 'color': '#666', 'marginBottom': '4px', 'display': 'block'}
_COL = {'flex': '1', 'marginRight': '12px'}
_CARD = {'background': '#f8f9fa', 'border': '1px solid #e0e0e0', 'borderRadius': '8px',
         'padding': '20px', 'marginBottom': '16px'}

STRATEGY_OPTIONS = [
    {'label': '無限攤平_V0', 'value': 'infinite_average_v0'},
    {'label': '逢跌加碼止盈', 'value': 'dip_and_take_profit'},
]


def _card(step, title, children):
    return html.Div([
        html.Div([
            html.Span(f"Step {step}", style={
                'background': '#1a73e8', 'color': '#fff', 'fontSize': '11px',
                'fontWeight': '600', 'padding': '2px 8px', 'borderRadius': '10px',
                'marginRight': '8px'}),
            html.Span(title, style={'fontSize': '14px', 'fontWeight': '600', 'color': '#333'}),
        ], style={'marginBottom': '16px'}),
        *children,
    ], style=_CARD)


def _num(id_, label, value, min_, max_, step):
    spec = {'id': id_, 'type': 'number', 'value': value, 'min': min_, 'step': step,
            'style': {**_INPUT}}
    if max_ is not None:
        spec['max'] = max_
    return html.Div([html.Label(label, style=_LABEL), dcc.Input(**spec)], style=_COL)


def _param_inputs(idx, strategy_class):
    if strategy_class == 'dip_and_take_profit':
        children = [
            _num({'type': 'param', 'idx': idx, 'name': 'dip_pct'},         '逢跌幅度(%)',    7, 1, 50, 0.5),
            _num({'type': 'param', 'idx': idx, 'name': 'take_profit_pct'}, '止盈幅度(%)',    5, 0.5, 50, 0.5),
            _num({'type': 'param', 'idx': idx, 'name': 'add_amount'},      '單次加碼(元)', 10000, 1000, None, 1000),
            _num({'type': 'param', 'idx': idx, 'name': 'max_position'},    '部位上限(元)', 100000, 10000, None, 10000),
            _num({'type': 'param', 'idx': idx, 'name': 'max_hold_days'},   '最長持有天數',  60, 1, None, 1),
        ]
    else:
        children = [
            _num({'type': 'param', 'idx': idx, 'name': 'dip_pct'},         '加碼/再進場跌幅(%)', 5, 1, 50, 0.5),
            _num({'type': 'param', 'idx': idx, 'name': 'take_profit_pct'}, '止盈幅度(%)',         5, 0.5, 50, 0.5),
            _num({'type': 'param', 'idx': idx, 'name': 'add_amount'},      '單次加碼(元)',      10000, 1000, None, 1000),
            _num({'type': 'param', 'idx': idx, 'name': 'max_position'},    '部位上限(元)',     100000, 10000, None, 10000),
        ]
    return html.Div(children, style={'display': 'flex', 'gap': '8px'})


def _ticker_row(idx, ticker):
    return html.Div([
        html.Div(ticker, style={'fontWeight': '600', 'width': '80px'}),
        html.Div([
            html.Label('策略', style=_LABEL),
            dcc.Dropdown(id={'type': 'strat-select', 'idx': idx},
                         options=STRATEGY_OPTIONS, value='infinite_average_v0',
                         clearable=False, style={'fontSize': '13px'}),
        ], style={'width': '180px', 'marginRight': '12px'}),
        html.Div(id={'type': 'param-block', 'idx': idx}, style={'flex': '1'}),
    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px',
              'padding': '8px', 'border': '1px solid #eee', 'borderRadius': '4px'})


def _render_results():
    r = current_result()
    if r is None:
        return html.Div('尚無回測結果，請完成上方設定後點擊「執行回測」。',
                        style={'color': '#999', 'padding': '20px 0', 'fontSize': '14px'})
    columns = [
        {'name': '標的', 'id': 'ticker', 'presentation': 'markdown'},
        {'name': '策略', 'id': 'strategy', 'presentation': 'markdown'},
        {'name': '拆股調整', 'id': 'split_adj'},
        {'name': '已實現損益', 'id': 'realized_pnl'},
        {'name': '未實現損益', 'id': 'unrealized_pnl'},
        {'name': '最終淨值', 'id': 'final_nav'},
        {'name': 'MDD', 'id': 'mdd'},
        {'name': 'Sharpe', 'id': 'sharpe'},
        {'name': 'Win Rate', 'id': 'win_rate'},
        {'name': 'Profit Factor', 'id': 'profit_factor'},
        {'name': 'Avg Hold (days)', 'id': 'avg_hold_days'},
    ]
    return html.Div([
        html.H2('回測結果', style={'marginBottom': '16px', 'fontSize': '18px'}),
        dcc.Graph(figure=portfolio_3line_chart(r.daily_snapshots),
                  style={'marginBottom': '24px'}),
        html.H3('每檔績效', style={'marginBottom': '8px', 'fontSize': '14px', 'opacity': '.7'}),
        dash_table.DataTable(
            data=per_ticker_rows(r), columns=columns,
            style_cell={'textAlign': 'left', 'padding': '8px 12px', 'fontSize': '13px'},
            style_header={'fontWeight': '600', 'opacity': '.6', 'fontSize': '11px'},
        ),
    ])


def layout() -> html.Div:
    return html.Div([
        _card(1, '選擇模式', [
            dcc.RadioItems(id='mode-radio', value='manual', inline=True,
                options=[
                    {'label': html.Span('個股（手動）', style={'marginLeft': '6px', 'marginRight': '28px'}), 'value': 'manual'},
                    {'label': html.Span('全隨機', style={'marginLeft': '6px', 'marginRight': '28px'}), 'value': 'random'},
                    {'label': html.Span('半隨機', style={'marginLeft': '6px'}), 'value': 'semi'},
                ],
                labelStyle={'cursor': 'pointer', 'fontSize': '13px'}),
        ]),
        _card(2, '標的與全域設定', [
            html.Div([
                html.Div([html.Label('起始日期', style=_LABEL),
                          dcc.Input(id='start-date', type='date', value='2026-01-01', style=_INPUT)], style=_COL),
                html.Div([html.Label('結束日期', style=_LABEL),
                          dcc.Input(id='end-date', type='date', value=date.today().isoformat(), style=_INPUT)], style=_COL),
                html.Div([html.Label('總資金 (元)', style=_LABEL),
                          dcc.Input(id='initial-capital', type='number', value=500000, min=10000, step=10000, style=_INPUT)], style=_COL),
                html.Div([html.Label('執行價', style=_LABEL),
                          dcc.Dropdown(id='exec-price',
                                       options=[{'label': '收盤價', 'value': 'close'},
                                                {'label': '開盤價', 'value': 'open'},
                                                {'label': 'VWAP', 'value': 'vwap'}],
                                       value='close', clearable=False)],
                         style={**_COL, 'marginRight': '0'}),
            ], style={'display': 'flex', 'marginBottom': '14px'}),
            html.Div([
                html.Label('股票代號（逗號分隔）', style=_LABEL),
                dcc.Input(id='tickers-input', type='text', value='2330',
                          placeholder='2330, 2317, 0050', style=_INPUT),
            ], id='sec-manual', style={'marginBottom': '4px'}),
            html.Div([
                html.Label('隨機選取檔數', style=_LABEL),
                dcc.Input(id='n-stocks', type='number', value=5, min=1, max=100, step=1,
                          style={**_INPUT, 'width': '120px'}),
            ], id='sec-n', style={'display': 'none'}),
            html.Div([
                html.Label('市場別', style={**_LABEL, 'marginTop': '10px'}),
                dcc.RadioItems(id='market-radio', value='all', inline=True,
                    options=[
                        {'label': html.Span('全部', style={'marginLeft': '5px', 'marginRight': '20px'}), 'value': 'all'},
                        {'label': html.Span('上市', style={'marginLeft': '5px', 'marginRight': '20px'}), 'value': 'TWSE'},
                        {'label': html.Span('上櫃', style={'marginLeft': '5px'}), 'value': 'TPEx'},
                    ]),
            ], id='sec-market', style={'display': 'none'}),
        ]),
        _card(3, '指派策略', [html.Div(id='strategy-assignments')]),
        html.Div([
            html.Button('執行回測', id='run-btn', n_clicks=0, style={
                'backgroundColor': '#1a73e8', 'color': '#fff', 'border': 'none',
                'borderRadius': '4px', 'padding': '10px 32px', 'fontSize': '14px',
                'cursor': 'pointer', 'fontWeight': '500'}),
            html.Span(id='run-error', style={'marginLeft': '16px', 'color': '#c62828', 'fontSize': '13px'}),
        ], style={'marginBottom': '28px'}),
        dcc.Loading(type='circle',
                    children=html.Div(id='home-content', children=_render_results())),
    ])


@callback(
    Output('sec-manual', 'style'), Output('sec-n', 'style'), Output('sec-market', 'style'),
    Input('mode-radio', 'value'),
)
def _toggle_sections(mode):
    show = {'marginBottom': '4px'}
    hide = {'display': 'none'}
    if mode == 'manual':
        return show, hide, hide
    if mode == 'random':
        return hide, show, hide
    return hide, show, {}


@callback(
    Output('strategy-assignments', 'children'),
    Input('mode-radio', 'value'),
    Input('tickers-input', 'value'),
)
def _render_assignments(mode, tickers_str):
    if mode == 'manual':
        tickers = [t.strip() for t in str(tickers_str or '').replace('，', ',').split(',') if t.strip()]
        if not tickers:
            return html.Div('請先在 Step 2 輸入股票代號',
                            style={'color': '#999', 'fontSize': '13px'})
        return [_ticker_row(i, t) for i, t in enumerate(tickers)]
    return _ticker_row(0, '(隨機抽中的所有 ticker 將共用同一策略)')


@callback(
    Output({'type': 'param-block', 'idx': MATCH}, 'children'),
    Input({'type': 'strat-select', 'idx': MATCH}, 'value'),
    State({'type': 'strat-select', 'idx': MATCH}, 'id'),
)
def _render_params(strat_class, id_):
    return _param_inputs(id_['idx'], strat_class)


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
    State('initial-capital', 'value'),
    State('exec-price', 'value'),
    State({'type': 'strat-select', 'idx': ALL}, 'value'),
    State({'type': 'param', 'idx': ALL, 'name': ALL}, 'value'),
    State({'type': 'param', 'idx': ALL, 'name': ALL}, 'id'),
    prevent_initial_call=True,
)
def _run_backtest(n, mode, tickers_str, start, end, n_stocks, market,
                  capital, exec_price, strat_classes, param_vals, param_ids):
    from data.provider import DataProvider
    from backtest.engine import BacktestEngine
    from backtest.models import TickerAssignment

    try:
        start_d = date.fromisoformat(start); end_d = date.fromisoformat(end)
    except (TypeError, ValueError):
        return no_update, '日期格式錯誤'
    if start_d >= end_d:
        return no_update, '起始日期須早於結束日期'

    provider = DataProvider()
    if mode == 'manual':
        tickers = [t.strip() for t in str(tickers_str or '').replace('，', ',').split(',') if t.strip()]
        if not tickers:
            return no_update, '請輸入股票代號'
    else:
        n_ = int(n_stocks or 5)
        tl = provider.get_ticker_list()
        if tl is None or tl.empty:
            return no_update, '無法取得股票清單'
        if mode == 'semi' and market and market != 'all':
            tl = tl[tl['market'] == market]
        if tl.empty:
            return no_update, '市場別無符合標的'
        import random as _rnd
        tickers = _rnd.sample(tl['ticker'].tolist(), min(n_, len(tl)))

    params_by_idx: dict[int, dict] = {}
    for pid, pval in zip(param_ids, param_vals):
        params_by_idx.setdefault(pid['idx'], {})[pid['name']] = float(pval)

    assignments = []
    if mode == 'manual':
        for i, ticker in enumerate(tickers):
            sc = strat_classes[i] if i < len(strat_classes) else 'infinite_average_v0'
            assignments.append(TickerAssignment(ticker, sc, params_by_idx.get(i, {})))
    else:
        sc = strat_classes[0] if strat_classes else 'infinite_average_v0'
        p = params_by_idx.get(0, {})
        for ticker in tickers:
            assignments.append(TickerAssignment(ticker, sc, dict(p)))

    for a in assignments:
        if 'dip_pct' in a.params:
            a.params['dip_pct'] /= 100.0
        if 'take_profit_pct' in a.params:
            a.params['take_profit_pct'] /= 100.0

    try:
        result = BacktestEngine(provider).run(
            assignments, start_d, end_d, float(capital), exec_price)
    except Exception as e:
        return no_update, f'回測失敗：{e}'

    set_results([result])
    return _render_results(), ''
