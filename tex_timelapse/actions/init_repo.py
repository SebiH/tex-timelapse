from tex_timelapse.actions.action import Action
from tex_timelapse.project import Project
from tex_timelapse.snapshot import Snapshot, SnapshotStatus


class InitRepoAction(Action):
    def getName(self) -> str:
        return "Init Repository"

    def init(self, project: Project) -> None:
        pass

    def cleanup(self) -> None:
        pass

    def run(self, snapshot: Snapshot) -> str:
        # workDir = snapshot.getWorkDir()
        cmd = f'git reset --hard {snapshot.commit_sha}'
        snapshot.execute_cmd(cmd)

        snapshot.main_tex_file = self.findMainTexFile(snapshot)
        snapshot.includes = self.findIncludedFiles(snapshot)

        # check for any changes to highlight them in the final output
        for file in snapshot.includes:
            diffCmd = f'git diff --unified=0 HEAD HEAD~1 {file}'
            diffOutput = snapshot.execute_cmd(diffCmd, ignore_error=True)
            if diffOutput != "":
                snapshot.gitDiff[file] = diffOutput

        return SnapshotStatus.COMPLETED


    def findMainTexFile(self, snapshot: Snapshot) -> str:
        result = snapshot.execute_cmd('find . -name *.tex -exec grep -l \\\\begin{document} {} +')
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

            resultInclude = snapshot.execute_cmd('grep -r \\\\include{ ' + unscanned_files[0], ignore_error=True)
            for line in resultInclude.splitlines():
                # ingore commented files
                if line.strip().startswith('%'):
                    continue

                # extract file name
                file = line.split('{')[1].split('}')[0]
                if not file.endswith('.tex'):
                    file += '.tex'
                new_files.append(file.strip())

            resultInput = snapshot.execute_cmd('grep -r \\\\input{ ' + unscanned_files[0], ignore_error=True)
            for line in resultInput.splitlines():
                # ingore commented files
                if line.strip().startswith('%'):
                    continue

                # extract file name
                file = line.split('{')[1].split('}')[0]
                if not file.endswith('.tex'):
                    file += '.tex'
                new_files.append(file.strip())

            resultGraphics = snapshot.execute_cmd('grep -r \\\\includegraphics ' + unscanned_files[0], ignore_error=True)
            for line in resultGraphics.splitlines():
                # ingore commented files
                if line.strip().startswith('%'):
                    continue

                # find index of 'includegraphics'
                idx = line.find('\\includegraphics')

                # extract file name
                file = line[idx:].split('{')[1].split('}')[0]

                # for images, we might need to add the extension
                has_extension = file.find('.') != -1
                if has_extension:
                    new_files.append(file.strip())
                else:
                    possible_files = snapshot.execute_cmd(f'find . -wholename *{file}.*')
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
