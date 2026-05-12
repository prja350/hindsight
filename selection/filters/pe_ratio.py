import pandas as pd
from selection.filters.base import BaseFilter

class PERatioFilter(BaseFilter):
    def __init__(self, min_pe: float = 0.0, max_pe: float = float('inf')) -> None:
        self.min_pe = min_pe
        self.max_pe = max_pe

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        return df[(df['pe_ratio'] >= self.min_pe) & (df['pe_ratio'] <= self.max_pe)].copy()
