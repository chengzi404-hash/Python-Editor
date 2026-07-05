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

class SuggestionExpert(ABC):
    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def suggest(self, block: SuggestionBlock) -> list:
        ...
    
    @abstractmethod
    def get_languange_exts(self) -> list:
        ...