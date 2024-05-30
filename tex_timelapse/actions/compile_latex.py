from typing import Dict, Set
from tex_timelapse.actions.action import Action
from tex_timelapse.project import Project
from tex_timelapse.snapshot import Snapshot, SnapshotStatus
import re
import os

class CompileLatexAction(Action):
    def getName(self) -> str:
        return "Compile LaTeX"

    def init(self, project: Project) -> None:
        self.latexCmd = project.config['latexCmd']
        # TODO: texliveonfly?
        pass

    def cleanup(self) -> None:
        pass

    def run(self, snapshot: Snapshot) -> str:
        workDir = snapshot.getWorkDir()
        texFile = snapshot.main_tex_file
        installCmd = f'texliveonfly {texFile}'

        # ignore errors in case it somehow still compiled
        snapshot.execute(installCmd, "latex", True)

        compileCmd = f"{self.latexCmd} {texFile}"
        # ignore errors in case it somehow still compiled
        snapshot.execute(compileCmd, "latex", True)

        # git format example: @@ -33,5 55,4 @@
        #                         ^  ^ ^  ^
        #                         |  | |  |
        #              Removed Line  | Added line
        #                            |    |
        #                      Number of removed / added lines (may be optional)
        #
        changedFiles: Dict[str, Set[int]] = {}
        for file, diff in snapshot.gitDiff.items():
            changedFiles[file] = set()

            if file.endswith(".tex"):
                # The following code extracts these values and puts both removed and added lines into the changedLines array
                gitDiffResults = re.finditer(r'@@\s+-(\d+),?(\d*)\s+\+(\d+),?(\d*)\s+@@', diff)
                for match in gitDiffResults:
                    for x in range(int(match.group(1)), int(match.group(1)) + int(match.group(2) if match.group(2) else 0) + 1):
                        changedFiles[file].add(x)
                    for x in range(int(match.group(3)), int(match.group(3)) + int(match.group(4) if match.group(4) else 0) + 1):
                        changedFiles[file].add(x)
            else:
                # since we might've added a file ending (but \includegraphics doesn't have to have one), we'll remove it again.
                # TODO: this assumes a file ending of 4 characters, which is not always the case
                basefile = file[:-4]
                if basefile.startswith("./"):
                    basefile = basefile[2:]

                # assuming it's an image file, all \includegraphics{...} lines are considered changed
                # TODO: potential issues:
                # - does not work if filename has a space in it -> execute should use array instead of string
                # - \includegraphics could be commented out
                # - \includegraphics could be split over multiple lines
                # - \includegraphics could be in in a macro
                # - we need to consider \graphicspath{...}
                occurrences = snapshot.execute(f'grep -rn \\\\includegraphics.*{basefile} .', 'latex', True)

                # this returns something like "file.tex:123:\includegraphics{file}"
                # -> we only need the line number and the file name
                for occurrence in occurrences.splitlines():
                    file = occurrence.split(":")[0]
                    line = int(occurrence.split(":")[1])
                    if changedFiles.get(file) is None:
                        changedFiles[file] = set()

                    changedFiles[file].add(line)


        changedPages = set()
        for file, changedLines in changedFiles.items():
            # convert the git changed lines to pages using synctex
            pdfFile = texFile[:-4] + ".pdf"
            for line in changedLines:
                filePath = file
                if not filePath.startswith("./"):
                    filePath = "./" + filePath

                synctexCmd = f'synctex view -i {line}:0:{os.path.abspath(workDir)}/{filePath} -o {pdfFile}'
                output = snapshot.execute(synctexCmd, "latex")

                result = re.search(r"Page:(\d*)", output, flags=re.MULTILINE)
                if (result):
                    page = int(result.group(1))
                    changedPages.add(page)

                # TODO: interpret this output correctly other than the page?
                # x = float(re.search(r"x:(\d*\.?\d*)", out, flags=re.MULTILINE).group(1))
                # y = float(re.search(r"y:(\d*\.?\d*)", out, flags=re.MULTILINE).group(1))
                # h = float(re.search(r"h:(\d*\.?\d*)", out, flags=re.MULTILINE).group(1))
                # v = float(re.search(r"v:(\d*\.?\d*)", out, flags=re.MULTILINE).group(1))
                # W = float(re.search(r"W:(\d*\.?\d*)", out, flags=re.MULTILINE).group(1))
                # H = float(re.search(r"H:(\d*\.?\d*)", out, flags=re.MULTILINE).group(1))


        # write pages back to file for later processing
        snapshot.changed_pages = list(changedPages)

        return SnapshotStatus.COMPLETED

    def reset(self, snapshot: Snapshot) -> None:
        pdfFile = snapshot.main_tex_file[:-4] + ".pdf"
        snapshot.changed_pages = []

        try:
            # remove all generated latex files
            os.remove(f'{snapshot.getWorkDir()}/latex/{pdfFile}')
            snapshot.execute('rm -f *.aux *.log *.out *.synctex.gz', 'latex', True)
        except:  # noqa: E722
            pass
