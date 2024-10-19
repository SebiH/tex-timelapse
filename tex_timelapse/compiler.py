import datetime
import os
import threading
import concurrent.futures
from typing import List
from ffmpeg_progress_yield import FfmpegProgress
from shutil import rmtree, copytree

from tex_timelapse.project import Project
from tex_timelapse.reporter import Reporter
from tex_timelapse.snapshot import Snapshot, SnapshotStatus
from tex_timelapse.util.serialization import saveToFile2
from tex_timelapse.actions.action import Action

def canRun(prevAction: str, action: Action, snapshot: Snapshot) -> bool:
    if prevAction != '':
        # prevAction did not run
        if prevAction not in snapshot.status:
            return False

        # prevAction failed
        if snapshot.status[prevAction] != SnapshotStatus.COMPLETED:
            return False

    return True


def compileSnapshot(project: Project, snapshot_sha: str, actions: List[Action], reporter: Reporter) -> Snapshot:
    return Snapshot("", "", datetime.datetime.now(), 0) # TODO
    # matching_snapshot = [s for s in project.snapshots if s.commit_sha == snapshot_sha]

    # if len(matching_snapshot) == 0:
    #     raise Exception(f"Snapshot {snapshot_sha} not found")
    # if len(matching_snapshot) > 1:
    #     raise Exception(f"Snapshot {snapshot_sha} found multiple times")

    # snapshot = matching_snapshot[0]
    # # TODO: snapshot.status = SnapshotStatus.PENDING
    # # TODO: snapshot.error = ''

    # prevAction = ''
    # for action in actions:
    #     if not canRun(prevAction, action, snapshot):
    #         continue

    #     snapshot.error = ''
    #     action.init(project)

    #     # Run job
    #     reporter.set_stage(action.getName(), 1)
    #     runAction(action, snapshot, reporter)
    #     action.cleanup()
    #     prevAction = action.getName()
    
    # return snapshot


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
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for snapshot in project.snapshots:
                future = executor.submit(compileSnapshot2, project, snapshot, actions, reporter)
                futures.append(future)
            
            for future in concurrent.futures.as_completed(futures):
                future.result()

            saveToFile2(f'{project.projectFolder}/snapshots.yaml', project.snapshots)

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



def compileSnapshot2(project: Project, snapshot: Snapshot, actions: List[Action], reporter: Reporter) -> None:
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