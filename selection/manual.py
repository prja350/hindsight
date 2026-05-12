from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from data.provider import DataProvider


@dataclass
class SelectionResult:
    tickers: list[str]
    start: date
    end: date


class ManualSelector:
    def __init__(self, tickers: list[str], start: date, end: date,
                 provider: DataProvider) -> None:
        self.tickers = tickers
        self.start = start
        self.end = end

    def select(self) -> SelectionResult:
        return SelectionResult(tickers=self.tickers, start=self.start, end=self.end)
