import pandas as pd
from selection.filters.base import BaseFilter

class VolumeFilter(BaseFilter):
    def __init__(self, min_volume: float = 0.0) -> None:
        self.min_volume = min_volume

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        return df[df['volume'] >= self.min_volume].copy()
