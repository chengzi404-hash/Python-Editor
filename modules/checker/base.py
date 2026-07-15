from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class OutputRow:
    message: str
    level: str

@dataclass
class Output:
    file: str
    row: list[OutputRow]

class Checker(ABC):
    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def check(self, file: str) -> Output:
        ...
