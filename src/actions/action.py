from abc import ABC, abstractmethod
from ..project import Project
from ..snapshot import Snapshot, SnapshotStatus

class Action(ABC):
    @abstractmethod
    def init(self, project: Project) -> None:
        pass

    @abstractmethod
    def run(self, snapshot: Snapshot) -> SnapshotStatus:
        pass

    @abstractmethod
    def cleanup(self) -> None:
        pass

    @abstractmethod
    def getName(self) -> str:
        pass