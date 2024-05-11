
from abc import ABC, abstractmethod

class Reporter(ABC):
    @abstractmethod
    def set_stage(self, name: str, length: int) -> None:
        pass

    @abstractmethod
    def add_progress(self) -> None:
        pass

    @abstractmethod
    def set_progress(self, num: float) -> None:
        pass

    @abstractmethod
    def log(self, msg: str) -> None:
        pass
