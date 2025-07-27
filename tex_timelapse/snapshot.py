from dataclasses import dataclass
from datetime import datetime
import subprocess
from typing import Any
import yaml
import shlex

class SnapshotStatus(object):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    FAILED = "Failed"

@dataclass
class Snapshot:
    def __init__(self, commit_sha: str, commit_date: datetime, index: int):
        self.commit_sha = commit_sha
        self.commit_date = commit_date
        self.index = int(index)
        self.main_tex_file = '' # will be set by InitRepoAction

        self.status: str = ''
        self.error = ''
        self.includes: list[str] = []
        #pdf_file: str

        self.pages: list[str] = []
        self.gitDiff: dict = {} # file -> changedLines
        self.changed_pages: list[dict] = []

    def setWorkDir(self, work_dir: str) -> None:
        self.work_dir = work_dir

    def getWorkDir(self) -> str:
        return self.work_dir

    def execute_cmd(self, cmd: str, ignore_error = False, posix=False) -> str:
        cwd = self.getWorkDir()

        output = subprocess.run(shlex.split(cmd, posix=posix), cwd=cwd, capture_output=True, text=True)
        if output.returncode != 0 and not ignore_error:
            self.error = output.stderr
            raise Exception(f"Command '{cmd}' failed with error: {output.stderr}")
        return output.stdout


    def to_dict(self) -> dict[str, Any]:
        return {
            'main_tex_file': self.main_tex_file,
            'commit_sha': self.commit_sha,
            'commit_date': self.commit_date,
            'index': self.index,
            'status': self.status,
            'error': self.error,
            'includes': list(self.includes),
            'gitDiff': self.gitDiff,
            'pages': self.pages,
            'changed_pages': list(self.changed_pages)
        }

    @staticmethod
    def serialize(file_path: str, snapshot: list['Snapshot']) -> None:
        with open(file_path, 'w') as file:
            file.write(yaml.dump([snap.to_dict() for snap in snapshot]))

    @staticmethod
    def deserialize(file_path: str) -> list['Snapshot']:
        with open(file_path, 'r') as file:
            data = yaml.load(file, Loader=yaml.CBaseLoader)
        
        snapshots: list['Snapshot'] = []
        for snap in data if data is not None else []:
            snapshot = Snapshot(
                commit_sha=snap["commit_sha"],
                commit_date=snap["commit_date"],
                index=int(snap["index"]),
            )
            snapshot.__dict__.update(snap)

            # for some reason, index is stored as a string in the yaml file
            snapshot.index = int(snapshot.index)

            snapshots.append(snapshot)

        return snapshots
