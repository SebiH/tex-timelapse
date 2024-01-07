import os
from multiprocessing.pool import ThreadPool
import multiprocessing
from typing import List
from ffmpeg_progress_yield import FfmpegProgress

from .project import Project
from .reporter import Reporter
from .snapshot import Snapshot, SnapshotStatus
from .util.serialization import saveToFile
from .actions.action import Action

pool = ThreadPool(multiprocessing.cpu_count())

def set_threads(threads: int):
    # dispose old pool
    pool.close()
    pool.join()

    pool = ThreadPool(threads)


# from .actions.init_repo import InitRepoJob
# from .jobs.compile_latex import CompileLatexJob
# from .jobs.pdf_to_image import PdfToImageJob
# from .jobs.assemble_image import AssembleImageJob
# jobs: List[Job] = [
#     InitRepoJob(),
#     CompileLatexJob(),
#     PdfToImageJob(),
#     AssembleImageJob()
# ]



def canRun(prevAction: str, action: Action, snapshot: Snapshot) -> bool:
    # action already complete
    if snapshot.status.get(action.getName()) == SnapshotStatus.COMPLETED:
        return False

    if prevAction is not None:
        # prevAction did not run
        if prevAction not in snapshot.status:
            return False

        # prevAction failed
        if snapshot.status[prevAction] != SnapshotStatus.COMPLETED:
            return False

    return True


def compileSnapshot(project: Project, snapshot_sha: str, actions: List[Action], reporter: Reporter):
    matching_snapshot = [s for s in project.snapshots if s.commit_sha == snapshot_sha]

    if len(matching_snapshot) == 0:
        raise Exception(f"Snapshot {snapshot_sha} not found")
    if len(matching_snapshot) > 1:
        raise Exception(f"Snapshot {snapshot_sha} found multiple times")

    snapshot = matching_snapshot[0]
    # TODO: snapshot.status = SnapshotStatus.PENDING
    # TODO: snapshot.error = ''

    prevAction = None
    for action in actions:
        if not canRun(prevAction, action, snapshot):
            break

        action.init(project)

        # Run job
        reporter.set_stage(action.getName(), 1)
        runAction(action, snapshot, reporter)
        action.cleanup()
        prevAction = action.getName()


def compileProject(project: Project, output: str, actions: List[Action], reporter: Reporter):

    prevAction = None
    for action in actions:
        action.init(project)

        reporter.set_stage(action.getName(), len(project.snapshots))
        snapshots = [s for s in project.snapshots if canRun(prevAction, action, s)]
        pool.map(lambda snapshot: runAction(action, snapshot, reporter), snapshots)

        action.cleanup()
        prevAction = action.getName()

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


def runAction(action: Action, snapshot: Snapshot, reporter: Reporter):
    snapshot.error = ''
    snapshot.status[action.getName()] = SnapshotStatus.IN_PROGRESS

    try:
        result = action.run(snapshot)
        snapshot.status[action.getName()] = result
    except Exception as e:
        snapshot.status[action.getName()] = SnapshotStatus.FAILED
        snapshot.error = str(e)
        reporter.log(f'Action "{action.getName()}" for snapshot {snapshot.commit_sha} failed with error: {e}')
    saveToFile(f'{snapshot.getWorkDir()}/snapshot.yaml', snapshot)
    reporter.add_progress()
