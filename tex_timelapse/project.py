from dataclasses import dataclass
import subprocess
from glob import glob
import os
import shutil
from typing import Any, Dict, List, Optional
import git
from slugify import slugify

from tex_timelapse.config import Config
from tex_timelapse.snapshot import Snapshot
import yaml

@dataclass
class Project:
    name: str
    projectFolder: str
    config: Config

    def __init__(self, name: str):
        self.name = name
        self.projectFolder = f'./projects/{slugify(self.name)}'
        self.snapshots: List[Snapshot] = []

    def loadSnapshots(self):
        self.snapshots = []

        # Load existing snapshots if file exists
        if os.path.exists(f'{self.projectFolder}/snapshots.yaml'):
            self.snapshots = Snapshot.deserialize(f'{self.projectFolder}/snapshots.yaml')
            print(f"Loaded {len(self.snapshots)} existing snapshots for project {self.name}")

        # Check if there are any missing snapshots
        repo = git.Repo(os.path.join(self.projectFolder, 'source'))
        missingCounter = 0
        indexCounter = len(self.snapshots)
        for commit in reversed(list(repo.iter_commits())):
            if commit.hexsha not in [snapshot.commit_sha for snapshot in self.snapshots]:
                missingCounter += 1
                sDict = Snapshot(commit.hexsha, commit.authored_date, indexCounter)
                indexCounter += 1
                self.snapshots.append(sDict)
        
        print(f"Added {missingCounter} missing snapshots")

        if missingCounter > 0:
            Snapshot.serialize(f'{self.projectFolder}/snapshots.yaml', self.snapshots)

        self.snapshots.sort(key=lambda x: x.index)


    def to_dict(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'config': self.config
        }

    @staticmethod
    def list() -> list['Project']:
        return [
            Project.deserialize(file.split('/')[1])
            for file in glob('projects/**/project.yaml', recursive=True)
        ]
    
    @staticmethod
    def deserialize(name: str, defaults: Optional[Dict[str, Any]] = None) -> 'Project':
        with open(f'./projects/{slugify(name)}/project.yaml', 'r') as f:
            data = yaml.safe_load(f)

        if defaults is None:
            defaults = {}

        project_data = {**defaults, **data}

        project = Project(project_data["name"])
        project.config = project_data["config"]
        return project


    @staticmethod
    def create(name: str, source: str) -> 'Project':
        print(f'Creating project "{name}" with default values...')
        
        project = Project(name)
        
        # create folder
        folder = f'./projects/{slugify(name)}'
        os.makedirs(folder, exist_ok=True)

        # init source folder
        os.makedirs(f'{folder}/source', exist_ok=True)

        # extract source zip into source folder
        if source.endswith('.zip'):
            shutil.unpack_archive(source, f'{folder}/source')
        else:
            raise Exception(f'Currently only zip source files are supported. Got: {source}')

        # clean up git for faster processing
        cmd = 'git gc --aggressive'

        output = subprocess.run(cmd.split(), cwd=f'{folder}/source', capture_output=False, text=True)
        if output.returncode != 0:
            raise Exception(f'"{cmd}" failed with error: {output.stderr}')

        # load default config
        with open('./default_config.yaml', 'r') as f:
            project.config = yaml.safe_load(f)

        project.serialize()

        # output
        print(f'Project "{name}" successfully initialized in "{folder}". Please edit the project.yaml file, then run:')
        print(f'tex-timelapse run {name} <output>')

        return project

    def serialize(self):
        with open(f'{self.projectFolder}/project.yaml', 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)
