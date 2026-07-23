"""Tests for tex_timelapse.actions.compile_latex: git-diff hunk parsing, and
CompileLatexAction.run's mapping from changed lines to synctex page
coordinates (with Snapshot.execute_cmd faked - no real LaTeX/synctex
involved)."""

from typing import List

import pytest

from tex_timelapse.actions.compile_latex import CompileLatexAction, parse_diff_hunks
from tex_timelapse.snapshot import Snapshot, SnapshotStatus


# ---------------------------------------------------------------------------
# parse_diff_hunks
# ---------------------------------------------------------------------------

def test_parse_diff_hunks_pure_addition():
    # note: the range is computed as range(start, start + count + 1), which
    # is inclusive of one line past the actual count on both sides - that's
    # existing behaviour of the code being extracted, not something this
    # test asserts is "correct" semantically.
    diff = "@@ -1,0 +2,3 @@\n+one\n+two\n+three\n"
    assert parse_diff_hunks(diff) == {1, 2, 3, 4, 5}


def test_parse_diff_hunks_pure_deletion():
    diff = "@@ -5,2 +4,0 @@\n-old1\n-old2\n"
    assert parse_diff_hunks(diff) == {4, 5, 6, 7}


def test_parse_diff_hunks_omitted_count_defaults_to_single_line():
    # git omits the ",N" count when N == 1
    diff = "@@ -3 +3 @@\n-old\n+new\n"
    assert parse_diff_hunks(diff) == {3}


def test_parse_diff_hunks_multiple_hunks_in_one_diff():
    diff = (
        "@@ -1,0 +2,1 @@\n+added\n"
        "@@ -10,1 +11,0 @@\n-removed\n"
    )
    assert parse_diff_hunks(diff) == {1, 2, 3, 10, 11}


def test_parse_diff_hunks_empty_diff_yields_no_lines():
    assert parse_diff_hunks('') == set()


def test_parse_diff_hunks_ignores_non_hunk_lines():
    diff = "diff --git a/f.tex b/f.tex\nindex 1234..5678 100644\n--- a/f.tex\n+++ b/f.tex\n@@ -1 +1 @@\n-a\n+b\n"
    assert parse_diff_hunks(diff) == {1}


# ---------------------------------------------------------------------------
# CompileLatexAction.run - fakes Snapshot.execute_cmd, no real LaTeX/synctex
# ---------------------------------------------------------------------------

class FakeProject:
    class config:
        latexCmd = 'latexmk -pdf -interaction=nonstopmode -synctex=1 -f'


SYNCTEX_OUTPUT_TEMPLATE = (
    "Page:{page}\nx:{x}\ny:{y}\nh:{h}\nv:{v}\nW:{W}\nH:{H}\n"
)


def _fake_execute_cmd_factory(synctex_calls: List[str], synctex_response: str):
    def _fake_execute_cmd(self, cmd, ignore_error=False, posix=False):
        if cmd.startswith('synctex'):
            synctex_calls.append(cmd)
            return synctex_response
        # texliveonfly / latexmk calls: nothing needed, the pdf existence
        # check reads the filesystem, not this return value.
        return ''
    return _fake_execute_cmd


def test_run_maps_git_diff_lines_to_pages_via_mocked_synctex(tmp_path, monkeypatch):
    # a compiled PDF must "exist" for CompileLatexAction to consider the
    # compile successful - content doesn't matter, it's never opened here.
    (tmp_path / 'main.pdf').write_bytes(b'%PDF-1.4 fake')

    snapshot = Snapshot('deadbeef', 1700000000, 0)
    snapshot.setWorkDir(str(tmp_path))
    snapshot.main_tex_file = './main.tex'
    snapshot.gitDiff = {
        # parse_diff_hunks resolves this single hunk to exactly one changed
        # line (see test_parse_diff_hunks_omitted_count_defaults_to_single_line)
        './chapter1.tex': "@@ -1 +1 @@\n-Hello world.\n+Hello world!\n",
    }

    synctex_calls: List[str] = []
    synctex_response = SYNCTEX_OUTPUT_TEMPLATE.format(page=1, x=10.0, y=20.0, h=1.0, v=2.0, W=100.0, H=12.0)
    monkeypatch.setattr(Snapshot, 'execute_cmd', _fake_execute_cmd_factory(synctex_calls, synctex_response))

    action = CompileLatexAction()
    action.init(FakeProject())
    result = action.run(snapshot)

    assert result == SnapshotStatus.COMPLETED
    # exactly one changed line -> one synctex call
    assert len(synctex_calls) == 1
    assert 'chapter1.tex' in synctex_calls[0]

    assert len(snapshot.changed_pages) == 1
    assert snapshot.changed_pages[0] == {'page': 1, 'x': 10.0, 'y': 20.0, 'h': 1.0, 'v': 2.0, 'W': 100.0, 'H': 12.0}


def test_run_fails_when_no_pdf_was_produced(tmp_path, monkeypatch):
    snapshot = Snapshot('deadbeef', 1700000000, 0)
    snapshot.setWorkDir(str(tmp_path))
    snapshot.main_tex_file = './main.tex'
    # no main.pdf written

    monkeypatch.setattr(Snapshot, 'execute_cmd', _fake_execute_cmd_factory([], ''))

    action = CompileLatexAction()
    action.init(FakeProject())
    result = action.run(snapshot)

    assert result == SnapshotStatus.FAILED


def test_run_with_no_diffs_produces_no_changed_pages(tmp_path, monkeypatch):
    (tmp_path / 'main.pdf').write_bytes(b'%PDF-1.4 fake')

    snapshot = Snapshot('deadbeef', 1700000000, 0)
    snapshot.setWorkDir(str(tmp_path))
    snapshot.main_tex_file = './main.tex'
    snapshot.gitDiff = {}

    monkeypatch.setattr(Snapshot, 'execute_cmd', _fake_execute_cmd_factory([], ''))

    action = CompileLatexAction()
    action.init(FakeProject())
    result = action.run(snapshot)

    assert result == SnapshotStatus.COMPLETED
    assert snapshot.changed_pages == []
