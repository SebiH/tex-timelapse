from typing import Dict, Set, List, Tuple
from tex_timelapse.actions.action import Action
from tex_timelapse.project import Project
from tex_timelapse.snapshot import Snapshot, SnapshotStatus
from pathlib import Path
import re
import os


def parse_diff_hunks(diff: str) -> Set[int]:
    """Parse `git diff --unified=0` hunk headers (e.g. '@@ -33,5 +55,4 @@')
    into the set of line numbers touched on either side of the hunk (both
    the removed range from the '-' side and the added range from the '+'
    side). The count after the comma is optional in git's own output when
    it's exactly 1.

    Extracted verbatim from CompileLatexAction.run for testability - no
    behaviour change.
    """
    changed: Set[int] = set()
    for match in re.finditer(r'@@\s+-(\d+),?(\d*)\s+\+(\d+),?(\d*)\s+@@', diff):
        for x in range(int(match.group(1)), int(match.group(1)) + int(match.group(2) if match.group(2) else 0) + 1):
            changed.add(x)
        for x in range(int(match.group(3)), int(match.group(3)) + int(match.group(4) if match.group(4) else 0) + 1):
            changed.add(x)
    return changed


class CompileLatexAction(Action):
    def getName(self) -> str:
        return 'Compile LaTeX'

    def init(self, project: Project) -> None:
        self.latexCmd = project.config.latexCmd
        # TODO: texliveonfly?
        pass

    def cleanup(self) -> None:
        pass

    def run(self, snapshot: Snapshot) -> str:
        workDir = snapshot.getWorkDir()
        texFile = snapshot.main_tex_file
        installCmd = f'texliveonfly {texFile}'

        # ignore errors in case it somehow still compiled
        snapshot.execute_cmd(installCmd, ignore_error=True)

        compileCmd = f'{self.latexCmd} {texFile}'
        # ignore errors in case it somehow still compiled
        output = snapshot.execute_cmd(compileCmd, ignore_error=True, posix=True)

        # check if the compilation was successful by checking if there's a pdf file
        pdfFile = texFile[:-4] + '.pdf'
        if not os.path.exists(f'{workDir}/{pdfFile}'):
            snapshot.error = output
            return SnapshotStatus.FAILED

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

            if file.endswith('.tex'):
                # extracts both removed and added line numbers from the diff hunks
                changedFiles[file] = parse_diff_hunks(diff)
            else:
                # since we might've added a file ending (but \includegraphics doesn't have to have one), we'll remove it again.
                # TODO: this assumes a file ending of 4 characters, which is not always the case
                basefile = file[:-4]
                if basefile.startswith('./'):
                    basefile = basefile[2:]

                # assuming it's an image file, all \includegraphics{...} lines are considered changed
                # TODO: potential issues:
                # - does not work if filename has a space in it -> execute should use array instead of string
                # - \includegraphics could be split over multiple lines
                # - \includegraphics could be in in a macro
                # - we need to consider \graphicspath{...}
                occurrences = self.findIncludeGraphicsOccurrences(Path(workDir), basefile)

                # this returns (file, line) pairs, e.g. ('./file.tex', 123)
                # -> we only need the line number and the file name
                for file, line in occurrences:
                    if changedFiles.get(file) is None:
                        changedFiles[file] = set()

                    changedFiles[file].add(line)


        changesPages = []
        for file, changedLines in changedFiles.items():
            # convert the git changed lines to pages using synctex
            pdfFile = texFile[:-4] + '.pdf'
            for line in changedLines:
                filePath = file
                if not filePath.startswith('./'):
                    filePath = './' + filePath

                synctexCmd = f'synctex view -i {line}:0:{os.path.abspath(workDir)}/{filePath} -o {pdfFile}'
                output = snapshot.execute_cmd(synctexCmd)

                pattern = r'Page:(?P<page>\d+)\nx:(?P<x>\d+\.?\d*)\ny:(?P<y>\d+\.?\d*)\nh:(?P<h>\d+\.?\d*)\nv:(?P<v>\d+\.?\d*)\nW:(?P<W>\d+\.?\d*)\nH:(?P<H>\d+\.?\d*)'
                synctexMatch = re.finditer(pattern, output, flags=re.MULTILINE)

                for m in synctexMatch:
                    changesPages.append({
                        'page': int(m.group('page')),
                        'x': float(m.group('x')),
                        'y': float(m.group('y')),
                        'h': float(m.group('h')),
                        'v': float(m.group('v')),
                        'W': float(m.group('W')),
                        'H': float(m.group('H')),
                    })


        # write pages back to file for later processing
        snapshot.changed_pages = changesPages

        return SnapshotStatus.COMPLETED


    def findIncludeGraphicsOccurrences(self, workDir: Path, basefile: str) -> List[Tuple[str, int]]:
        """Replacement for `grep -rn \\includegraphics.*{basefile} .` (BSD/GNU
        grep dialects differ enough on this to be a portability concern, and
        spawning grep over the whole tree per changed non-.tex file is slow).

        \\includegraphics only ever appears in .tex sources, so we only need
        to scan those rather than every file in the work dir. Returns
        (file, line) pairs shaped like the old 'file.tex:123:...' output,
        with file './'-prefixed the same way `grep -rn ... .` would print it.

        Note: unlike the old grep call, `basefile` is treated as a literal
        string (via re.escape) rather than a BRE, so characters like '.' in
        a path no longer act as wildcards. This is a deliberate behaviour
        change: the old regex-injection was already dialect-dependent
        (GNU/BSD BRE differ on several metacharacters), so treating it as a
        literal is strictly more correct and portable, not just different."""
        pattern = re.compile(r'\\includegraphics.*' + re.escape(basefile))
        results: List[Tuple[str, int]] = []

        texFiles = [p for p in workDir.rglob('*.tex') if '.git' not in p.relative_to(workDir).parts]
        for texFile in sorted(texFiles, key=lambda p: p.relative_to(workDir).as_posix()):
            try:
                content = texFile.read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue

            relPath = f'./{texFile.relative_to(workDir).as_posix()}'
            for lineNo, line in enumerate(content.splitlines(), start=1):
                if pattern.search(line):
                    results.append((relPath, lineNo))

        return results

    def reset(self, snapshot: Snapshot) -> None:
        # automatically resets due to compilation in temp. runner
        pass
