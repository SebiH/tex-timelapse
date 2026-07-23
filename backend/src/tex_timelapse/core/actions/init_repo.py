from tex_timelapse.core.actions.action import Action
from tex_timelapse.core.project import Project
from tex_timelapse.core.snapshot import Snapshot, SnapshotStatus
from pathlib import Path
from typing import Optional
import fnmatch


class InitRepoAction(Action):
    def getName(self) -> str:
        return "Init Repository"

    def init(self, project: Project) -> None:
        self.concatCommits = project.config.concatCommits

    def cleanup(self) -> None:
        pass

    def run(self, snapshot: Snapshot) -> str:
        # workDir = snapshot.getWorkDir()
        cmd = f'git reset --hard {snapshot.commit_sha}'
        snapshot.execute_cmd(cmd)

        snapshot.main_tex_file = self.findMainTexFile(snapshot)
        snapshot.includes = self.findIncludedFiles(snapshot)

        diffHistory = 1 if self.concatCommits <= 0 else self.concatCommits

        # check for any changes to highlight them in the final output
        for file in snapshot.includes:
            diffCmd = f'git diff --unified=0 HEAD~{diffHistory} HEAD {file}'
            diffOutput = snapshot.execute_cmd(diffCmd, ignore_error=True)
            if diffOutput != "":
                snapshot.gitDiff[file] = diffOutput

        return SnapshotStatus.COMPLETED


    def readFileSafe(self, path: Path) -> Optional[str]:
        """Read a file as UTF-8 (tolerating latin-1 etc. via errors='replace').
        Returns None if the file cannot be read, mirroring the tolerance the
        old ignore_error=True grep/find calls had for missing files."""
        try:
            return path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            return None

    def iterAllFiles(self, workDir: Path) -> list[Path]:
        """All regular files under workDir, sorted by relative path for
        deterministic results (the old `find` order was filesystem-dependent).
        The .git directory is skipped - it never contains .tex/asset sources
        we care about and walking it was a pure waste of time."""
        files = [
            p for p in workDir.rglob('*')
            if p.is_file() and '.git' not in p.relative_to(workDir).parts
        ]
        return sorted(files, key=lambda p: p.relative_to(workDir).as_posix())

    def findMainTexFile(self, snapshot: Snapshot) -> str:
        workDir = Path(snapshot.getWorkDir())
        texFiles = [p for p in self.iterAllFiles(workDir) if p.suffix == '.tex']

        for texFile in texFiles:
            content = self.readFileSafe(texFile)
            if content is not None and '\\begin{document}' in content:
                relPath = texFile.relative_to(workDir).as_posix()
                return f'./{relPath}'

        raise Exception("Could not find main .tex file")

    def nonCommentLines(self, workDir: Path, filePath: str) -> list[str]:
        """Lines of filePath (relative to workDir), skipping any whose
        stripped form starts with '%' (LaTeX comments). Note: this only
        skips lines that START with '%' - an inline `foo % \\input{bar}`
        is still picked up, matching the pre-existing (and questionable)
        behaviour of the old grep-based scan."""
        content = self.readFileSafe(workDir / filePath)
        if content is None:
            return []
        return [line for line in content.splitlines() if not line.strip().startswith('%')]

    def findFilesMatchingWholename(self, workDir: Path, stem: str) -> list[str]:
        """Replacement for `find . -wholename *{stem}.*` (a GNU extension
        that does not exist on BSD/macOS find). Matches any file whose
        './'-prefixed relative path contains the literal stem followed by
        a dot, anywhere in the path - the same shape as the old wholename
        glob."""
        pattern = f'*{stem}.*'
        matches = []
        for path in self.iterAllFiles(workDir):
            candidate = f'./{path.relative_to(workDir).as_posix()}'
            if fnmatch.fnmatch(candidate, pattern):
                matches.append(candidate)
        return matches

    # TODO: consider more commands, e.g. \bibliography{...}, \addbibresource{...}, \lstinputlisting{...}
    def findIncludedFiles(self, snapshot: Snapshot) -> list[str]:
        workDir = Path(snapshot.getWorkDir())
        included_files = [ snapshot.main_tex_file ]
        unscanned_files = [ snapshot.main_tex_file ]

        while len(unscanned_files) > 0:
            new_files = []

            lines = self.nonCommentLines(workDir, unscanned_files[0])

            for line in lines:
                if '\\include{' not in line:
                    continue

                # extract file name
                file = line.split('{')[1].split('}')[0]
                if not file.endswith('.tex'):
                    file += '.tex'
                new_files.append(file.strip())

            for line in lines:
                if '\\input{' not in line:
                    continue

                # extract file name
                file = line.split('{')[1].split('}')[0]
                if not file.endswith('.tex'):
                    file += '.tex'
                new_files.append(file.strip())

            for line in lines:
                if '\\addbibresource{' not in line:
                    continue

                # extract file name
                file = line.split('{')[1].split('}')[0]
                if not file.endswith('.bib'):
                    file += '.bib'
                new_files.append(file.strip())

            for line in lines:
                if '\\includegraphics' not in line:
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
                    possible_files = self.findFilesMatchingWholename(workDir, file)
                    for pf in possible_files:
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
