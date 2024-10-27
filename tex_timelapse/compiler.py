import os
import threading
import concurrent.futures
from typing import List
from ffmpeg_progress_yield import FfmpegProgress
from shutil import rmtree, copytree

from tex_timelapse.project import Project
from tex_timelapse.reporter import Reporter
from tex_timelapse.snapshot import Snapshot, SnapshotStatus
from tex_timelapse.actions.action import Action

executor = concurrent.futures.ThreadPoolExecutor()

def setThreads(threads: int) -> None:
    global executor
    executor = concurrent.futures.ThreadPoolExecutor(threads)

def canRun(prevAction: str, action: Action, snapshot: Snapshot) -> bool:
    if prevAction != '':
        # prevAction did not run
        if prevAction not in snapshot.status:
            return False

        # prevAction failed
        if snapshot.status[prevAction] != SnapshotStatus.COMPLETED:
            return False

    return True



def initFolder(project: Project, id: int) -> str:
    # generate unique folder name via uuid
    workDir = f"{project.projectFolder}/workdir/{id}"
    # check if workdir already exists
    if not os.path.exists(workDir):
        copytree(f'{project.projectFolder}/source/.git', f'{workDir}/.git', dirs_exist_ok=True)
    return workDir

def cleanupFolder(project: Project, folder: str) -> None:
    rmtree(f"{folder}/latex", ignore_errors=True)

def compileProject(project: Project, output: str, actions: List[Action], reporter: Reporter) -> None:

    reporter.set_stage("Compiling snapshots", len(project.snapshots))

    try:
        futures = []
        for snapshot in project.snapshots:
            future = executor.submit(compileSnapshot, project, snapshot, actions, reporter)
            futures.append(future)
        
        for future in concurrent.futures.as_completed(futures):
            future.result()

        Snapshot.serialize(f'{project.projectFolder}/snapshots.yaml', project.snapshots)

    except Exception as e:
        print(f"Error: {e}")

    rmtree(f"{project.projectFolder}/workdir", ignore_errors=True)

    # render video
    reporter.set_stage("Rendering video", 100)
    os.makedirs(f'{project.projectFolder}/frames', exist_ok=True)

    os.makedirs(f'{project.projectFolder}/output', exist_ok=True)
    framerate = project.config['framerate']
    cmd = f"""ffmpeg -y -framerate {framerate}
        -pattern_type glob -i {project.projectFolder}/frames/*.png
        -c:v libx264 -movflags +faststart
        -vf format=yuv420p,scale=iw*0.25:ih*0.25,pad=ceil(iw/2)*2:ceil(ih/2)*2:0:0:white
        -strict -2 {project.projectFolder}/frames/{output}.mp4
    """

    ff = FfmpegProgress([ c.strip() for c in cmd.split(' ') if c != ''])
    for progress in ff.run_command_with_progress():
        reporter.set_progress(progress / 100)



def compileSnapshot(project: Project, snapshot: Snapshot, actions: List[Action], reporter: Reporter) -> None:
    thread_id = threading.get_ident()

    workDir = initFolder(project, thread_id)
    snapshot.setWorkDir(workDir)

    prevAction = ''
    for action in actions:
        if not canRun(prevAction, action, snapshot):
            prevAction = action.getName()
            continue

        action.init(project)
        snapshot.status[action.getName()] = SnapshotStatus.IN_PROGRESS
        reporter.update_progress(snapshot)

        try:
            result = action.run(snapshot)
            snapshot.status[action.getName()] = result
        except Exception as e:
            snapshot.status[action.getName()] = SnapshotStatus.FAILED
            snapshot.error = str(e)
            reporter.log(f'Action "{action.getName()}" for snapshot {snapshot.commit_sha} failed with error: {e}')
        
        action.cleanup()
        prevAction = action.getName()
        reporter.update_progress(snapshot)
    
    reporter.add_progress(snapshot)