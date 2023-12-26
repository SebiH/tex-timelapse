from datetime import datetime
from enum import Enum
import subprocess
import os

class SnapshotStatus(object):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    FAILED = "Failed"


class Snapshot:
    # for serialization
    # TODO: is there a better way to do this?
    def __init__(self):
        pass

    def __init__(self, project_dir: str, commit_sha: str, commit_date: datetime, main_tex_file: str):
        self.project_dir = project_dir
        self.commit_sha = commit_sha
        self.commit_date = commit_date
        self.main_tex_file = main_tex_file

        self.status: dict[str, str] = {}
        self.error = ''

        # \include{...}, \input{...}, \includegraphics{...},
        # \bibliography{...}, \addbibresource{...}, \lstinputlisting{...}
        self.includes: list[str] = []
        #pdf_file: str

        #pages: list[str] = []
        self.gitDiff: dict[str, ] = '' # file -> changedLines
        self.changed_pages: list[int] = []


    def getWorkDir(self) -> str:
        return os.path.join(self.project_dir, 'snapshots', self.commit_sha)

    def execute(self, cmd: str, folder: str = None) -> str:
        cwd = self.getWorkDir()
        if folder is not None:
            cwd = os.path.join(cwd, folder)

        output = subprocess.run(cmd.split(), cwd=cwd, capture_output=True, text=True)
        if output.returncode != 0:
            self.error = output.stderr
            raise Exception(f"Command '{cmd}' failed with error: {output.stderr}")
        return output.stdout
