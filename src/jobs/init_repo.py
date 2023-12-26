from .job import Job
from ..projectconfig import ProjectConfig
from ..snapshot import Snapshot, SnapshotStatus
from shutil import rmtree, copytree


class InitRepoJob(Job):
    def getName(self) -> str:
        return "Init Repository"

    def init(self, project_dir: str) -> None:
        pass

    def cleanup(self) -> None:
        pass

    def run(self, snapshot: Snapshot, config: ProjectConfig) -> SnapshotStatus:
        workDir = snapshot.getWorkDir()
        copytree(f'{snapshot.project_dir}/{config["sourceFolder"]}/.git', f'{workDir}/latex/.git')
        cmd = f'git reset --hard {snapshot.commit_sha}'
        snapshot.execute(cmd, "latex")

        # TODO: find main .tex file
        # TODO: find all included files

        # TODO: for each, check if there are any changes
        diffCmd = f'git diff --unified=0 HEAD HEAD~1 {snapshot.main_tex_file}'
        snapshot.gitDiff = snapshot.execute(diffCmd, "latex")

        # save space
        rmtree(f'{workDir}/latex/.git')
        return SnapshotStatus.COMPLETED
