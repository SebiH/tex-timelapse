"""Tests for tex_timelapse.core.actions.replace_text.

Regression coverage for the directory-guard bug: the text-replacement loop
guarded on os.path.exists(file), resolving the workdir-relative path against
the process CWD instead of work_dir, so it was always False and the config's
text_replacements never applied.
"""

from tex_timelapse.core.actions.replace_text import ReplaceTextAction
from tex_timelapse.core.snapshot import Snapshot, SnapshotStatus


class FakeProject:
    class config:
        text_replacements = [
            {'old': 'X', 'new': 'C'},
            {'old': '3', 'new': '3'},
        ]


def _make_action(replacements):
    action = ReplaceTextAction()

    class P:
        class config:
            text_replacements = replacements

    action.init(P())
    return action


def test_text_replacements_actually_rewrite_a_workdir_file(tmp_path, monkeypatch):
    # run from a *different* CWD than the workdir, to prove the guard resolves
    # against work_dir and not the process CWD (the bug this regresses).
    monkeypatch.chdir(tmp_path)
    work_dir = tmp_path / 'work'
    work_dir.mkdir()
    (work_dir / 'main.tex').write_text(
        '\\documentclass{article}\\begin{document}X cubed = X^3\\end{document}',
        encoding='utf-8',
    )

    snapshot = Snapshot('deadbeef', 1700000000, 0)
    snapshot.setWorkDir(str(work_dir))
    snapshot.main_tex_file = './main.tex'
    snapshot.includes = ['./main.tex']

    action = _make_action([{'old': 'X', 'new': 'C'}])
    result = action.run(snapshot)

    assert result == SnapshotStatus.COMPLETED
    rewritten = (work_dir / 'main.tex').read_text(encoding='utf-8')
    assert 'C cubed = C^3' in rewritten
    assert 'X' not in rewritten


def test_includeonly_is_stripped_from_main_tex(tmp_path):
    work_dir = tmp_path / 'work'
    work_dir.mkdir()
    (work_dir / 'main.tex').write_text(
        '\\includeonly{chapter1}\n\\documentclass{article}\n\\begin{document}\n\\end{document}\n',
        encoding='utf-8',
    )

    snapshot = Snapshot('deadbeef', 1700000000, 0)
    snapshot.setWorkDir(str(work_dir))
    snapshot.main_tex_file = './main.tex'
    snapshot.includes = ['./main.tex']

    action = _make_action([])
    action.run(snapshot)

    rewritten = (work_dir / 'main.tex').read_text(encoding='utf-8')
    assert '\\includeonly' not in rewritten
    # the rest of the document survives
    assert '\\begin{document}' in rewritten


def test_missing_included_file_is_skipped_not_fatal(tmp_path):
    work_dir = tmp_path / 'work'
    work_dir.mkdir()
    (work_dir / 'main.tex').write_text('\\begin{document}\\end{document}', encoding='utf-8')

    snapshot = Snapshot('deadbeef', 1700000000, 0)
    snapshot.setWorkDir(str(work_dir))
    snapshot.main_tex_file = './main.tex'
    # a .tex that was resolved from an \include but does not exist on disk
    snapshot.includes = ['./main.tex', './ghost.tex']

    action = _make_action([{'old': 'a', 'new': 'b'}])
    # must not raise on the missing ghost.tex
    assert action.run(snapshot) == SnapshotStatus.COMPLETED
