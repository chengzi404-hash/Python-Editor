from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SuggestionBlock:
    code: str
    position: int


@dataclass
class DOMScope:
    begin: int
    end: int
    varibles: list
    functions: list
    classes: list
    subDOM: "list[DOMScope]"


@dataclass
class SuggestionItem:
    """A single suggestion with priority for sorting.

    Attributes:
        label: Display text for the suggestion
        priority: Lower value = higher priority (appears first)
        kind: Category hint ('keyword', 'builtin', 'function', 'class', 'variable')
    """
    label: str
    priority: int = 0
    kind: str = ''


class SuggestionExpert(ABC):
    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def suggest(self, block: SuggestionBlock) -> list[SuggestionItem]:
        ...

    @abstractmethod
    def get_languange_exts(self) -> list:
        ...
