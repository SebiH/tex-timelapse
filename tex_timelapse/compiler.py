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

def initFolder(project: Project, id: int) -> str:
    workDir = f"{project.projectFolder}/workdir/{id}"

    if not os.path.exists(workDir):
        copytree(f'{project.projectFolder}/source/.git', f'{workDir}/.git', dirs_exist_ok=True)

    return workDir

def cleanupFolder(project: Project, folder: str) -> None:
    rmtree(f"{folder}/latex", ignore_errors=True)

def compileProject(project: Project, output: str, actions: List[Action], reporter: Reporter) -> None:
    snapshot_count = len(project.snapshots)
    concat_commits = project.config.get('concatCommits', -1)
    if concat_commits > 0:
        snapshot_count = snapshot_count // concat_commits

    reporter.set_stage("Compiling snapshots", snapshot_count)

    # skip commits if concat commits is enabled, but start with the first commit
    skip_count = concat_commits

    try:
        pending_snapshots = []
        for snapshot in project.snapshots:
            # skip # of commits if concat commits is enabled
            if concat_commits > 0 and skip_count < concat_commits:
                skip_count += 1
                continue
            pending_snapshots.append(snapshot)
            skip_count = 0

        retry_count = 0

        while len(pending_snapshots) > 0 and (retry_count < concat_commits // 2 or concat_commits == -1):
            futures = []
            for snapshot in pending_snapshots:
                future = executor.submit(compileSnapshot, project, snapshot, actions, reporter)
                futures.append(future)

            retry_count += 1
            pending_snapshots = []

            # Await results from compilation
            for future in concurrent.futures.as_completed(futures):
                completed_snapshot = future.result()
                
                # retry compilation if we skipped commits from concatention anyway
                if concat_commits > 0 and completed_snapshot.status == SnapshotStatus.FAILED:
                    # progressively try previous snapshots if available - maybe we can find a working one
                    snapshot_index = next((i for i, snapshot in enumerate(project.snapshots) if snapshot.commit_sha == completed_snapshot.commit_sha), -1)
                    if snapshot_index > 0:
                        previous_snapshot = project.snapshots[snapshot_index - 1]
                        pending_snapshots.append(previous_snapshot)
                        reporter.log(f'Retrying snapshot {completed_snapshot.commit_sha} ({retry_count}/{concat_commits // 2})')

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
        -strict -2 {project.projectFolder}/output/{output}.mp4
    """

    ff = FfmpegProgress([ c.strip() for c in cmd.split(' ') if c != ''])
    for progress in ff.run_command_with_progress():
        reporter.set_progress(progress / 100)



def compileSnapshot(project: Project, snapshot: Snapshot, actions: List[Action], reporter: Reporter) -> Snapshot:
    thread_id = threading.get_ident()

    workDir = initFolder(project, thread_id)
    snapshot.setWorkDir(workDir)

    snapshot.status = SnapshotStatus.IN_PROGRESS
    reporter.update_progress(snapshot)

    for action in actions:
        action.init(project)

        try:
            result = action.run(snapshot)
        except Exception as e:
            result = SnapshotStatus.FAILED
            snapshot.error = str(e)
            reporter.log(f'Action "{action.getName()}" for snapshot {snapshot.commit_sha} failed with error: {e}')
        
        if result == SnapshotStatus.FAILED:
            snapshot.status = SnapshotStatus.FAILED
            break

        action.cleanup()
    
    if snapshot.status != SnapshotStatus.FAILED:
        snapshot.status = SnapshotStatus.COMPLETED
    # else:
    #     # retry if concat commits is enabled
    #     if project.config['concatCommits'] and snapshot.concat_commit_retry_count < project.config['concatCommitsMax'] // 2:
    #         snapshot.concat_commit_retry_count += 1
    #         reporter.log(f'Retrying snapshot {snapshot.commit_sha} ({snapshot.concat_commit_retry_count}/{project.config["concatCommitsMax"] // 2})')
    #         return compileSnapshot(project, snapshot, actions, reporter)

    reporter.add_progress(snapshot)
    return snapshot
