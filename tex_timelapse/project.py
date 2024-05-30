import subprocess
from glob import glob
import os
import shutil
from typing import List
import git
from slugify import slugify

from tex_timelapse.config import Config
from tex_timelapse.snapshot import Snapshot
from tex_timelapse.util.serialization import loadFromFile

def init_project(name: str, source: str) -> str:
    print(f"Initializing project '{name}' with default values...")
    
    # create folder
    folder = f'./projects/{slugify(name)}'
    os.makedirs(folder, exist_ok=True)

    # init source folder
    os.makedirs(f'{folder}/source', exist_ok=True)

    # extract source zip into source folder
    if source.endswith('.zip'):
        shutil.unpack_archive(source, f'{folder}/source')
    else:
        raise Exception(f"Currently only zip source files are supported. Got: {source}")

    # clean up git for faster processing
    cmd = 'git gc --aggressive'

    output = subprocess.run(cmd.split(), cwd=f'{folder}/source', capture_output=False, text=True)
    if output.returncode != 0:
        raise Exception(f"'{cmd}' failed with error: {output.stderr}")

    # copy default config
    shutil.copyfile('./default_config.yaml', f'{folder}/project.yaml')

    # output
    print(f"Project '{name}' successfully initialized in '{folder}'. Please edit the project.yaml file, then run:")
    print(f"tex-timelapse run {name} <output>")

    return slugify(name)


class Project:
    name: str
    projectFolder: str
    config: Config

    def __init__(self, name: str):
        self.name = slugify(name)
        self.projectFolder = f'./projects/{self.name}'

        default_values = {
            'todo': 'todo',
        }
        full_config = {**default_values, **loadFromFile(f'{self.projectFolder}/project.yaml')}

        self.config = Config(**full_config)

        self.snapshots: List[Snapshot] = []
        self.initSnapshots()

    def initSnapshots(self):
        self.snapshots = []

        # Load existing snapshots
        for file in glob(f'{self.projectFolder}/snapshots/**/snapshot.yaml'):
            sDict = loadFromFile(file)
            if sDict:
                snapshot = Snapshot("", "", None)
                snapshot.__dict__ = sDict # TODO: is there a better way to do this?
                self.snapshots.append(snapshot)
        print(f"Loaded {len(self.snapshots)} existing snapshots")

        # Check if there are any missing snapshots
        repo = git.Repo(os.path.join(self.projectFolder, 'source'))
        missingCounter = 0
        for commit in list(repo.iter_commits()):
            if commit.hexsha not in [snapshot.commit_sha for snapshot in self.snapshots]:
                missingCounter += 1
                sDict = Snapshot(self.projectFolder, commit.hexsha, commit.authored_date)
                self.snapshots.append(sDict)
        
        print(f"Added {missingCounter} missing snapshots")

        # order snapshots by date
        self.snapshots.sort(key=lambda x: x.commit_date)


def list_projects() -> list[str]:
    return [
        os.path.dirname(file).removeprefix('projects/')
        for file in glob('projects/**/project.yaml', recursive=True)
    ]
