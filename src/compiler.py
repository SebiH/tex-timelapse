import os
from multiprocessing.pool import ThreadPool
import multiprocessing
from typing import List
from ffmpeg_progress_yield import FfmpegProgress

from .project import Project
from .reporter import Reporter
from .snapshot import Snapshot, SnapshotStatus
from .util.serialization import saveToFile
from .jobs.job import Job

pool = ThreadPool(multiprocessing.cpu_count())

def set_threads(threads: int):
    # dispose old pool
    pool.close()
    pool.join()

    pool = ThreadPool(threads)


# from .jobs.init_repo import InitRepoJob
# from .jobs.compile_latex import CompileLatexJob
# from .jobs.pdf_to_image import PdfToImageJob
# from .jobs.assemble_image import AssembleImageJob
# jobs: List[Job] = [
#     InitRepoJob(),
#     CompileLatexJob(),
#     PdfToImageJob(),
#     AssembleImageJob()
# ]



def canRun(prevJob: str, job: Job, snapshot: Snapshot) -> bool:
    # job already complete
    if snapshot.status.get(job.getName()) == SnapshotStatus.COMPLETED:
        return False

    if prevJob is not None:
        # prevjob did not run
        if prevJob not in snapshot.status:
            return False

        # prevjob failed
        if snapshot.status[prevJob] != SnapshotStatus.COMPLETED:
            return False

    return True


def compileSnapshot(project: Project, snapshot_sha: str, jobs: List[Job], reporter: Reporter):
    matching_snapshot = [s for s in project.snapshots if s.commit_sha == snapshot_sha]

    if len(matching_snapshot) == 0:
        raise Exception(f"Snapshot {snapshot_sha} not found")
    if len(matching_snapshot) > 1:
        raise Exception(f"Snapshot {snapshot_sha} found multiple times")

    snapshot = matching_snapshot[0]
    # TODO: snapshot.status = SnapshotStatus.PENDING
    # TODO: snapshot.error = ''

    prevJob = None
    for job in jobs:
        if not canRun(prevJob, job, snapshot):
            break

        job.init(project)

        # Run job
        reporter.set_stage(job.getName(), 1)
        runJob(job, snapshot, reporter)
        job.cleanup()
        prevJob = job.getName()


def compileProject(project: Project, output: str, jobs: List[Job], reporter: Reporter):

    prevJob = None
    for job in jobs:
        job.init(project)

        reporter.set_stage(job.getName(), len(project.snapshots))
        snapshots = [s for s in project.snapshots if canRun(prevJob, job, s)]
        pool.map(lambda snapshot: runJob(job, snapshot, reporter), snapshots)

        job.cleanup()
        prevJob = job.getName()

    # render video
    reporter.set_stage("Rendering video", 1)
    os.makedirs(f'{project.projectFolder}/output', exist_ok=True)

    framerate = project.config['framerate']
    cmd = f"""
        ffmpeg -y -framerate {framerate}
        -pattern_type glob -i {project.projectFolder}/frames/*.png
        -c:v libx264 -movflags +faststart
        -vf format=yuv420p,scale=iw*0.25:ih*0.25,pad=ceil(iw/2)*2:ceil(ih/2)*2:0:0:white
        -strict -2 {project.projectFolder}/output/{output}.mp4
    """

    ff = FfmpegProgress([ c.strip() for c in cmd.split(' ') if c != ''])
    for progress in ff.run_command_with_progress():
        reporter.set_progress(progress / 100)


def runJob(job: Job, snapshot: Snapshot, reporter: Reporter):
    snapshot.error = ''
    snapshot.status[job.getName()] = SnapshotStatus.IN_PROGRESS

    try:
        result = job.run(snapshot)
        snapshot.status[job.getName()] = result
    except Exception as e:
        snapshot.status[job.getName()] = SnapshotStatus.FAILED
        snapshot.error = str(e)
        reporter.log(f'Job "{job.getName()}" for snapshot {snapshot.commit_sha} failed with error: {e}')
    saveToFile(f'{snapshot.getWorkDir()}/snapshot.yaml', snapshot)
    reporter.add_progress()
