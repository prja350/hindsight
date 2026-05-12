from __future__ import annotations
import random
from datetime import date
from typing import TYPE_CHECKING

from selection.filters.base import BaseFilter
from selection.manual import SelectionResult

if TYPE_CHECKING:
    from data.provider import DataProvider


class SemiRandomSelector:
    def __init__(self, n: int, start: date, end: date,
                 filters: list[BaseFilter], provider: DataProvider) -> None:
        self.n = n
        self.start = start
        self.end = end
        self.filters = filters
        self.provider = provider

    def select(self) -> SelectionResult:
        df = self.provider.get_ticker_list()
        if df is None or df.empty:
            return SelectionResult(tickers=[], start=self.start, end=self.end)
        for f in self.filters:
            df = f.apply(df)
            if df.empty:
                break
        all_tickers = df['ticker'].tolist()
        n = min(self.n, len(all_tickers))
        chosen = random.sample(all_tickers, n) if n > 0 else []
        return SelectionResult(tickers=chosen, start=self.start, end=self.end)
