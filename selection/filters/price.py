import pandas as pd
from selection.filters.base import BaseFilter

class PriceFilter(BaseFilter):
    def __init__(self, min_price: float = 0.0, max_price: float = float('inf')) -> None:
        self.min_price = min_price
        self.max_price = max_price

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        return df[(df['close'] >= self.min_price) & (df['close'] <= self.max_price)].copy()
