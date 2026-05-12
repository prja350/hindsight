import pandas as pd
from selection.filters.base import BaseFilter

class VolatilityFilter(BaseFilter):
    def __init__(self, min_vol: float = 0.0) -> None:
        self.min_vol = min_vol

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        return df[df['volatility'] >= self.min_vol].copy()
