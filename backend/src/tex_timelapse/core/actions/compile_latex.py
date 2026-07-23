from typing import Dict, Set, List, Tuple
from tex_timelapse.actions.action import Action
from tex_timelapse.project import Project
from tex_timelapse.snapshot import Snapshot, SnapshotStatus
from pathlib import Path
import re
import os


def _texliveonfly_engine(latexCmd: str) -> str:
    """Pick the base TeX engine texliveonfly should probe with.

    texliveonfly detects missing packages by running a base engine and
    parsing its log, defaulting to pdflatex. If the project is built with
    lualatex or xelatex, probing with pdflatex resolves the wrong package
    set (or fails outright on a document that only compiles under lualatex) -
    which is the likely cause of the long-standing 'diss: not compiling
    (lualatex?)' bug in todo.txt.

    We match the engine name anywhere in the configured command, so this
    covers both a bare `lualatex ...` latexCmd and latexmk's
    `-pdflatex='lualatex %O %S'` form (the shape the web UI's compiler
    dropdown emits)."""
    lowered = latexCmd.lower()
    if 'lualatex' in lowered:
        return 'lualatex'
    if 'xelatex' in lowered:
        return 'xelatex'
    return 'pdflatex'


def parse_diff_hunks(diff: str) -> Set[int]:
    """Parse `git diff --unified=0` hunk headers (e.g. '@@ -33,5 +55,4 @@')
    into the set of line numbers touched on either side of the hunk (both
    the removed range from the '-' side and the added range from the '+'
    side).

    A hunk header is `@@ -a,b +c,d @@`: the removed side starts at line `a`
    and spans `b` lines, the added side starts at `c` and spans `d`. git
    omits the ',count' when the count is exactly 1, so a missing count means
    one line; an explicit count of 0 (e.g. `-33,0` for a pure insertion)
    means that side touches no lines. The changed lines are therefore
    range(start, start + count), not start + count + 1 - the old code added
    a spurious extra line to every hunk with an explicit count."""
    changed: Set[int] = set()
    for match in re.finditer(r'@@\s+-(\d+),?(\d*)\s+\+(\d+),?(\d*)\s+@@', diff):
        removed_start = int(match.group(1))
        removed_count = int(match.group(2)) if match.group(2) else 1
        added_start = int(match.group(3))
        added_count = int(match.group(4)) if match.group(4) else 1
        changed.update(range(removed_start, removed_start + removed_count))
        changed.update(range(added_start, added_start + added_count))
    return changed


class CompileLatexAction(Action):
    def getName(self) -> str:
        return 'Compile LaTeX'

    def init(self, project: Project) -> None:
        self.latexCmd = project.config.latexCmd
        self.engine = _texliveonfly_engine(self.latexCmd)

    def cleanup(self) -> None:
        pass

    def run(self, snapshot: Snapshot) -> str:
        workDir = snapshot.getWorkDir()
        texFile = snapshot.main_tex_file
        compileCmd = f'{self.latexCmd} {texFile}'
        pdfFile = texFile[:-4] + '.pdf'
        pdfPath = f'{workDir}/{pdfFile}'

        # Compile first, and only fall back to texliveonfly when no PDF
        # appears - the symptom of a missing package. This used to call
        # texliveonfly unconditionally before every compile.
        #
        # The point is NOT raw speed on a full TeX install: there, running
        # texliveonfly first is actually marginally faster, because its
        # pdflatex pass primes the .aux so the following latexmk needs fewer
        # passes (measured ~29.5s vs ~33s over the 9-commit sample). The point
        # is the minimal-install path (the Docker scheme-small image, the
        # common deployment): the old code paid texliveonfly's full
        # package-detection compile - and its network probing - on every
        # single snapshot, even long after the needed packages were installed.
        # Compiling first means that cost is paid only by snapshots that
        # actually fail for a missing package; once the package is installed
        # (the TeX tree is shared across snapshots) later commits compile
        # straight through.
        #
        # ignore errors in case it somehow still compiled
        output = snapshot.execute_cmd(compileCmd, ignore_error=True, posix=True)

        if not os.path.exists(pdfPath):
            # No PDF - possibly a missing package. Pull missing packages with
            # texliveonfly (probing with the configured engine, not its
            # pdflatex default), then compile once more. On a system with a
            # complete TeX install this branch never runs; it exists for
            # minimal installs (e.g. the Docker image's scheme-small) that
            # rely on on-demand package installation.
            installCmd = f'texliveonfly -c {self.engine} {texFile}'
            snapshot.execute_cmd(installCmd, ignore_error=True)
            output = snapshot.execute_cmd(compileCmd, ignore_error=True, posix=True)

        # check if the compilation was successful by checking if there's a pdf file
        if not os.path.exists(pdfPath):
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
