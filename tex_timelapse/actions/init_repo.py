from tex_timelapse.actions.action import Action
from tex_timelapse.project import Project
from tex_timelapse.snapshot import Snapshot, SnapshotStatus
from shutil import rmtree, copytree


class InitRepoAction(Action):
    def getName(self) -> str:
        return "Init Repository"

    def init(self, project: Project) -> None:
        self.sourceFolder = f'{project.projectFolder}/source'
        pass

    def cleanup(self) -> None:
        pass

    def run(self, snapshot: Snapshot) -> str:
        workDir = snapshot.getWorkDir()
        copytree(f'{snapshot.project_dir}/{self.sourceFolder}/.git', f'{workDir}/latex/.git', dirs_exist_ok=True)
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
