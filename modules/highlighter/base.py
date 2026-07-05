from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class HighlightToken:
    start: int
    end: int
    type: str


@dataclass
class HighlightBlock:
    code: str
    tokens: list[HighlightToken] | None = None


class HighlighterExpert(ABC):
    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def highlight(self, block: HighlightBlock) -> HighlightBlock:
        ...

    @abstractmethod
    def get_languange_exts(self) -> list:
        ...
