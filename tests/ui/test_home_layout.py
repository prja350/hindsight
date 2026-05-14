from __future__ import annotations


def test_layout_has_capital_and_exec_inputs():
    import dash
    dash.Dash(__name__, suppress_callback_exceptions=True)
    from ui.pages.home import layout
    html = str(layout())
    assert 'initial-capital' in html
    assert 'exec-price' in html


def test_default_dates_set_to_2026_to_today():
    import dash
    dash.Dash(__name__, suppress_callback_exceptions=True)
    from ui.pages.home import layout
    html = str(layout())
    assert '2026-01-01' in html
