from abc import ABC, abstractmethod
from ..projectconfig import ProjectConfig
from ..snapshot import Snapshot, SnapshotStatus

class Job(ABC):
    @abstractmethod
    def init(self, project_dir: str) -> None:
        pass

    @abstractmethod
    def run(self, snapshot: Snapshot, config: ProjectConfig) -> SnapshotStatus:
        pass

    @abstractmethod
    def cleanup(self) -> None:
        pass

    @abstractmethod
    def getName(self) -> str:
        pass