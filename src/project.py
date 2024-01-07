from glob import glob
import os
from typing import List
import git
from slugify import slugify

from .config import Config
from .snapshot import Snapshot, SnapshotStatus
from .util.serialization import loadFromFile

class Project:
    name: str
    projectFolder: str
    config: Config

    def __init__(self, name: str):
        self.name = slugify(name);
        self.projectFolder = f'./projects/{self.name}'
        self.config = loadFromFile(f'{self.projectFolder}/project.yaml')

        self.snapshots: List[Snapshot] = []
        self.initSnapshots()

    def initSnapshots(self):
        # Load existing snapshots
        for file in glob(f'{self.projectFolder}/snapshots/**/snapshot.yaml'):
            sDict = loadFromFile(file)
            if sDict:
                snapshot = Snapshot("", "", None, "")
                snapshot.__dict__ = sDict # TODO: is there a better way to do this?
                self.snapshots.append(snapshot)
        print(f"Loaded {len(self.snapshots)} existing snapshots")

        # Check if there are any missing snapshots
        repo = git.Repo(os.path.join(self.projectFolder, self.config['sourceFolder']))
        missingCounter = 0
        for commit in list(repo.iter_commits()):
            if commit.hexsha not in [snapshot.commit_sha for snapshot in self.snapshots]:
                missingCounter += 1
                sDict = Snapshot(self.projectFolder, commit.hexsha, commit.authored_date, self.config['mainTexFile'])
                self.snapshots.append(sDict)
        
        print(f"Added {missingCounter} missing snapshots")

    def setStage(self, stage: int):
        for snapshot in self.snapshots:
            for job in self.jobs[stage-1:]:
                snapshot.status[job.getName()] = SnapshotStatus.PENDING



def list_projects() -> list[Project]:
    return [
        os.path.dirname(file).removeprefix('projects/')
        for file in glob(f'projects/**/project.yaml', recursive=True)
    ]
