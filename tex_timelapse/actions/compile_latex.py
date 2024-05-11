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
        try:
            snapshot.execute(installCmd, "latex")
        except:
            # ignore errors in case it somehow still compiled
            pass

        compileCmd = f"{self.latexCmd} {texFile}"
        try:
            snapshot.execute(compileCmd, "latex")
        except:
            # ignore errors in case it somehow still compiled
            pass

        changedLines = set()

        # git format example: @@ -33,5 55,4 @@
        #                         ^  ^ ^  ^
        #                         |  | |  |
        #              Removed Line  | Added line
        #                            |    |
        #                      Number of removed / added lines (may be optional)
        #
        # The following code extracts these values and puts both removed and added lines into the changedLines array
        gitDiffResults = re.finditer(r'@@\s+-(\d+),?(\d*)\s+\+(\d+),?(\d*)\s+@@', snapshot.gitDiff)
        for match in gitDiffResults:
            for x in range(int(match.group(1)), int(match.group(1)) + int(match.group(2) if match.group(2) else 0) + 1):
                changedLines.add(x)
            for x in range(int(match.group(3)), int(match.group(3)) + int(match.group(4) if match.group(4) else 0) + 1):
                changedLines.add(x)

        # convert the git changed lines to pages using synctex
        changedPages = set()
        pdfFile = texFile[:-4] + ".pdf"
        for line in changedLines:
            # TODO: only works for main tex file, not for included files
            synctexCmd = f'synctex view -i {line}:0:{os.path.abspath(workDir)}/./{texFile} -o {pdfFile}'
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

