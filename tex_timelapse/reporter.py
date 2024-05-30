
from abc import ABC, abstractmethod
from typing import Optional

from tex_timelapse.snapshot import Snapshot

class Reporter(ABC):
    @abstractmethod
    def set_stage(self, name: str, length: int) -> None:
        pass

    @abstractmethod
    def add_progress(self, snapshot: Snapshot) -> None:
        pass

    @abstractmethod
    def update_progress(self, snapshot: Snapshot) -> None:
        pass

    @abstractmethod
    def set_progress(self, num: float) -> None:
        pass

    @abstractmethod
    def log(self, msg: str, snapshot: Optional[Snapshot] = None) -> None:
        pass
