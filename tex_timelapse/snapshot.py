from datetime import datetime
import subprocess
import os
import shlex

class SnapshotStatus(object):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    FAILED = "Failed"


class Snapshot:
    def __init__(self, project_dir: str, commit_sha: str, commit_date: datetime, index: int):
        self.project_dir = project_dir
        self.commit_sha = commit_sha
        self.commit_date = commit_date
        self.index = index
        self.main_tex_file = '' # will be set by InitRepoAction

        self.status: dict[str, str] = {}
        self.error = ''
        self.includes: list[str] = []
        #pdf_file: str

        self.pages: list[str] = []
        self.gitDiff: dict = {} # file -> changedLines
        self.changed_pages: list[dict] = []
        self.changed_pages_test: list[list[float]] = []

    def setWorkDir(self, work_dir: str) -> None:
        self.work_dir = work_dir

    def getWorkDir(self) -> str:
        return self.work_dir

    def execute(self, cmd: str, sub_folder: str = '', ignore_error = False, posix=False) -> str:
        cwd = self.getWorkDir()
        if sub_folder != '':
            cwd = os.path.join(self.project_dir, 'snapshots', self.commit_sha, sub_folder)
            if not os.path.exists(cwd):
                os.makedirs(cwd, exist_ok=True)

        output = subprocess.run(shlex.split(cmd, posix=posix), cwd=cwd, capture_output=True, text=True)
        if output.returncode != 0 and not ignore_error:
            self.error = output.stderr
            raise Exception(f"Command '{cmd}' failed with error: {output.stderr}")
        return output.stdout


    def to_dict(self) -> dict:
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