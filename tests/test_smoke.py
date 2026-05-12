def test_all_layers_importable():
    from data.provider import DataProvider
    from selection.semi_random import SemiRandomSelector
    from strategy.dip_and_take_profit import DipAndTakeProfitStrategy
    from backtest.engine import BacktestEngine
    from ui.components.charts import portfolio_line_chart
    from ui.components.tables import strategy_metrics_rows
    assert True
