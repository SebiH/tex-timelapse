from abc import ABC, abstractmethod
from tex_timelapse.project import Project
from tex_timelapse.snapshot import Snapshot

class Action(ABC):
    @abstractmethod
    def init(self, project: Project) -> None:
        pass

    @abstractmethod
    def run(self, snapshot: Snapshot) -> str:
        pass

    @abstractmethod
    def cleanup(self) -> None:
        pass

    @abstractmethod
    def getName(self) -> str:
        pass

    @abstractmethod
    def reset(self, snapshot: Snapshot) -> None:
        pass