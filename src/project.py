from datetime import datetime
from glob import glob
from multiprocessing.pool import ThreadPool
import os
from typing import List
from alive_progress import alive_bar
from ffmpeg_progress_yield import FfmpegProgress
import git
from slugify import slugify

from .projectconfig import ProjectConfig
from .snapshot import Snapshot, SnapshotStatus
from .util.serialization import loadFromFile, saveToFile
from .util.dotdict import dotdict

from .jobs.job import Job
from .jobs.init_repo import InitRepoJob
from .jobs.compile_latex import CompileLatexJob
from .jobs.pdf_to_image import PdfToImageJob
from .jobs.assemble_image import AssembleImageJob

class TimelapseProject:
    name: str
    config: ProjectConfig
    projectFolder: str

    def __init__(self, name: str, config: dotdict):
        self.name = name;
        self.config = config
        self.projectFolder = f'projects/{self.name}'

        self.snapshots: List[Snapshot] = []
        self.initSnapshots()

        self.jobs: List[Job] = [
            InitRepoJob(),
            CompileLatexJob(),
            PdfToImageJob(),
            AssembleImageJob()
        ]


    def log(self, message: str):
        print(f'[{datetime.now()}] {message}')


    def initSnapshots(self):
        # Load existing snapshots
        for file in glob(f'projects/{self.name}/snapshots/**/snapshot.yaml'):
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

    def compileSnapshot(self, snapshot_sha: str):
        prevJob: str = None
        for job in self.jobs:
            job.init(self.projectFolder)

            # Filter snapshots
            eligibleSnapshots = []
            for snapshot in self.snapshots:
                if snapshot.commit_sha != snapshot_sha:
                    continue

                if snapshot.status.get(job.getName()) == SnapshotStatus.COMPLETED:
                    continue

                # prevjob did not run
                if prevJob is not None and prevJob not in snapshot.status:
                    continue

                # prevjob failed
                if prevJob is not None and snapshot.status[prevJob] != SnapshotStatus.COMPLETED:
                    continue

                snapshot.error = ''
                eligibleSnapshots.append(snapshot)

            # Run job
            print(job.getName())
            pool = ThreadPool(self.config['workers'])

            with alive_bar(len(eligibleSnapshots)) as bar:
                if self.config['useMultithreading']:
                    pool.map(lambda snapshot: self.runJob(job, snapshot, bar), eligibleSnapshots)
                else:
                    for snapshot in eligibleSnapshots:
                        bar.text = f"{snapshot.commit_date} ({snapshot.commit_sha})"
                        self.runJob(job, snapshot, bar)

            pool.close()
            pool.join()

            prevJob = job.getName()
            job.cleanup()


    def run(self, output: str):
        prevJob: str = None
        for job in self.jobs:
            job.init(self.projectFolder)

            # Filter snapshots
            eligibleSnapshots = []
            for snapshot in self.snapshots:
                if snapshot.status.get(job.getName()) == SnapshotStatus.COMPLETED:
                    continue

                # prevjob did not run
                if prevJob is not None and prevJob not in snapshot.status:
                    continue

                # prevjob failed
                if prevJob is not None and snapshot.status[prevJob] != SnapshotStatus.COMPLETED:
                    continue

                snapshot.error = ''
                eligibleSnapshots.append(snapshot)

            # Run job
            print(job.getName())
            pool = ThreadPool(self.config['workers'])

            with alive_bar(len(eligibleSnapshots)) as bar:
                if self.config['useMultithreading']:
                    pool.map(lambda snapshot: self.runJob(job, snapshot, bar), eligibleSnapshots)
                else:
                    for snapshot in eligibleSnapshots:
                        bar.text = f"{snapshot.commit_date} ({snapshot.commit_sha})"
                        self.runJob(job, snapshot, bar)

            pool.close()
            pool.join()

            prevJob = job.getName()
            job.cleanup()
    
        # render video
        os.makedirs(f'{self.projectFolder}/output', exist_ok=True)

        print("Rendering video")
        framerate = self.config['framerate']
        cmd = f'ffmpeg -y -framerate {framerate} -pattern_type glob -i {self.projectFolder}/frames/*.png -c:v libx264 -movflags +faststart -vf format=yuv420p,scale=iw*0.25:ih*0.25,pad=ceil(iw/2)*2:ceil(ih/2)*2:0:0:white -strict -2 {self.projectFolder}/output/{output}.mp4'
        ff = FfmpegProgress(cmd.split(' '))
        with alive_bar(manual=True) as bar:
            for progress in ff.run_command_with_progress():
                bar(progress / 100)


    def runJob(self, job: Job, snapshot: Snapshot, bar):
        # try:
        result = job.run(snapshot, self.config)
        snapshot.status[job.getName()] = result
        # except Exception as e:
        #     snapshot.status[job.getName()] = SnapshotStatus.FAILED
        #     snapshot.error = str(e)
        #     self.log(f'Job "{job.getName()}" for snapshot {snapshot.commit_sha} failed with error: {e}')
        saveToFile(f'{snapshot.getWorkDir()}/snapshot.yaml', snapshot);
        bar()


def list_projects() -> list[TimelapseProject]:
    return [
        os.path.dirname(file).removeprefix('projects/')
        for file in  glob(f'projects/**/project.yaml', recursive=True)
    ]


def load_project(name: str) -> TimelapseProject:
    # load project from file
    projectName = slugify(name)
    config: ProjectConfig = loadFromFile(f'./projects/{projectName}/project.yaml')
    project = TimelapseProject(projectName, config)
    return project