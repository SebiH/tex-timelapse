from tex_timelapse.actions.action import Action
from tex_timelapse.project import Project
from tex_timelapse.snapshot import Snapshot, SnapshotStatus
from shutil import rmtree, copytree


class InitRepoAction(Action):
    def getName(self) -> str:
        return "Init Repository"

    def init(self, project: Project) -> None:
        self.sourceFolder = f'{project.projectFolder}/source'

    def cleanup(self) -> None:
        pass

    def run(self, snapshot: Snapshot) -> str:
        workDir = snapshot.getWorkDir()
        copytree(f'{self.sourceFolder}/.git', f'{workDir}/latex/.git', dirs_exist_ok=True)
        cmd = f'git reset --hard {snapshot.commit_sha}'
        snapshot.execute(cmd, "latex")

        snapshot.main_tex_file = self.findMainTexFile(snapshot)
        snapshot.includes = self.findIncludedFiles(snapshot)

        # check for any changes to highlight them in the final output
        for file in snapshot.includes:
            diffCmd = f'git diff --unified=0 HEAD HEAD~1 {file}'
            diffOutput = snapshot.execute(diffCmd, "latex", True)
            if diffOutput != "":
                snapshot.gitDiff[file] = diffOutput

        # save space
        rmtree(f'{workDir}/latex/.git')
        return SnapshotStatus.COMPLETED


    def findMainTexFile(self, snapshot: Snapshot) -> str:
        result = snapshot.execute('find . -name *.tex -exec grep -l \\\\begin{document} {} +', 'latex')
        if result == "":
            raise Exception("Could not find main .tex file")

        # use the first line as result
        result = result.splitlines()[0]

        return result.strip()



    # TODO: consider more commands, e.g. \bibliography{...}, \addbibresource{...}, \lstinputlisting{...}
    def findIncludedFiles(self, snapshot: Snapshot) -> list[str]:
        included_files = [ snapshot.main_tex_file ]
        unscanned_files = [ snapshot.main_tex_file ]

        while len(unscanned_files) > 0:
            new_files = []

            resultInclude = snapshot.execute('grep -r \\\\include{ ' + unscanned_files[0], 'latex', True)
            for line in resultInclude.splitlines():
                # extract file name
                file = line.split('{')[1].split('}')[0]
                if not file.endswith('.tex'):
                    file += '.tex'
                new_files.append(file.strip())

            resultInput = snapshot.execute('grep -r \\\\input{ ' + unscanned_files[0], 'latex', True)
            for line in resultInput.splitlines():
                # extract file name
                file = line.split('{')[1].split('}')[0]
                if not file.endswith('.tex'):
                    file += '.tex'
                new_files.append(file.strip())

            resultGraphics = snapshot.execute('grep -r \\\\includegraphics ' + unscanned_files[0], 'latex', True)
            for line in resultGraphics.splitlines():
                # extract file name
                file = line.split('{')[1].split('}')[0]

                # for images, we might need to add the extension
                has_extension = file.find('.') != -1
                if has_extension:
                    new_files.append(file.strip())
                else:
                    possible_files = snapshot.execute(f'find . -wholename *{file}.*', 'latex')
                    for pf in possible_files.splitlines():
                        new_files.append(pf.strip())

            for file in new_files:
                if file not in included_files:
                    included_files.append(file)

                    if file.endswith('.tex'):
                        unscanned_files.append(file)

            unscanned_files.remove(unscanned_files[0])
        
        return included_files

    def reset(self, snapshot: Snapshot) -> None:
        snapshot.gitDiff = {}
        snapshot.includes = []
        cwd = snapshot.getWorkDir()
        rmtree(f'{cwd}/latex', ignore_errors=True)
