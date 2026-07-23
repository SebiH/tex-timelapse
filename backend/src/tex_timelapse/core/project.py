from dataclasses import dataclass
import subprocess
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional
import git
from slugify import slugify

from tex_timelapse.core.config import Config
from tex_timelapse.core.snapshot import Snapshot
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

        else:
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
            'config': self.config.to_dict()
        }

    @staticmethod
    def list() -> list['Project']:
        projects = []
        for file in Path('projects').glob('**/project.yaml'):
            with open(file, 'r') as f:
                data = yaml.safe_load(f)
            name = data.get('name') if data else None
            if name:
                projects.append(Project.deserialize(name))
        return projects

    @staticmethod
    def _load_default_config_dict() -> Dict[str, Any]:
        """Raw contents of default_config.yaml, used as the fallback for
        any config field missing from a project's own project.yaml."""
        try:
            with open('./default_config.yaml', 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}

    @staticmethod
    def deserialize(name: str, defaults: Optional[Dict[str, Any]] = None) -> 'Project':
        with open(f'./projects/{slugify(name)}/project.yaml', 'r') as f:
            data = yaml.safe_load(f) or {}

        # config fields missing from this project's own project.yaml fall
        # back to default_config.yaml; `defaults` lets a caller layer
        # additional overrides on top of that.
        default_config = Project._load_default_config_dict()
        if defaults:
            default_config = {**default_config, **defaults}

        project = Project(data["name"])
        project.config = Config.from_dict(data.get("config"), defaults=default_config)
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
        default_config = Project._load_default_config_dict()
        project.config = Config.from_dict(default_config, defaults=default_config)

        project.serialize()

        # output
        print(f'Project "{name}" successfully initialized in "{folder}". Please edit the project.yaml file, then run:')
        print(f'tex-timelapse run {name} <output>')

        return project

    def serialize(self):
        with open(f'{self.projectFolder}/project.yaml', 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)
