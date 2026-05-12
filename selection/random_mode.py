from __future__ import annotations
import random
from datetime import date, timedelta
from typing import TYPE_CHECKING

from selection.manual import SelectionResult

if TYPE_CHECKING:
    from data.provider import DataProvider

_POOL_YEARS = 5


class RandomSelector:
    def __init__(self, n: int, provider: DataProvider,
                 start: date | None = None, end: date | None = None) -> None:
        self.n = n
        self.provider = provider
        self._start = start
        self._end = end

    def select(self) -> SelectionResult:
        ticker_df = self.provider.get_ticker_list()
        all_tickers = ticker_df['ticker'].tolist() if ticker_df is not None else []
        n = min(self.n, len(all_tickers))
        chosen = random.sample(all_tickers, n)

        if self._start and self._end:
            return SelectionResult(tickers=chosen, start=self._start, end=self._end)

        today = date.today()
        pool_start = today - timedelta(days=365 * _POOL_YEARS)
        max_offset = max(0, (today - pool_start).days - 365)
        offset = random.randint(0, max_offset)
        start = pool_start + timedelta(days=offset)
        end = start + timedelta(days=random.randint(180, 365))
        return SelectionResult(tickers=chosen, start=start, end=end)
