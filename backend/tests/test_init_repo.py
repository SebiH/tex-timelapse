"""Tests for tex_timelapse.actions.init_repo: main-.tex discovery, the
\\include/\\input/\\addbibresource/\\includegraphics resolution walk, the
wholename matching helper, and (as a regression) the direction of the
`git diff` command InitRepoAction.run shells out to."""

from tex_timelapse.actions.init_repo import InitRepoAction
from tex_timelapse.snapshot import Snapshot, SnapshotStatus


def test_find_main_tex_file(plain_workdir, make_snapshot):
    snapshot = make_snapshot(work_dir=plain_workdir)
    action = InitRepoAction()
    assert action.findMainTexFile(snapshot) == './main.tex'


def test_find_main_tex_file_raises_when_absent(tmp_path, make_snapshot):
    (tmp_path / 'notex.txt').write_text('nothing here')
    snapshot = make_snapshot(work_dir=tmp_path)
    action = InitRepoAction()
    try:
        action.findMainTexFile(snapshot)
        assert False, 'expected an exception'
    except Exception as e:
        assert 'Could not find main .tex file' in str(e)


def test_find_included_files_resolves_input_addbibresource_and_includegraphics(plain_workdir, make_snapshot):
    snapshot = make_snapshot(work_dir=plain_workdir)
    action = InitRepoAction()
    snapshot.main_tex_file = action.findMainTexFile(snapshot)
    included = action.findIncludedFiles(snapshot)

    assert './main.tex' in included
    assert 'chapter1.tex' in included          # \input{chapter1}
    assert 'chapter2.tex' in included          # \include{chapter2}
    assert 'refs.bib' in included               # \addbibresource{refs.bib}
    assert './diagram.png' in included          # \includegraphics{diagram} via wholename match


def test_find_included_files_only_queues_tex_files_for_further_scanning(plain_workdir, make_snapshot):
    # chapter1.tex/chapter2.tex have no further includes of their own in the
    # fixture, so the walk should terminate without raising or looping.
    snapshot = make_snapshot(work_dir=plain_workdir)
    action = InitRepoAction()
    snapshot.main_tex_file = action.findMainTexFile(snapshot)
    included = action.findIncludedFiles(snapshot)
    assert isinstance(included, list)
    assert len(included) == len(set(included))  # no duplicates


def test_find_files_matching_wholename(plain_workdir):
    action = InitRepoAction()
    matches = action.findFilesMatchingWholename(plain_workdir, 'diagram')
    assert matches == ['./diagram.png']


def test_find_files_matching_wholename_no_match(plain_workdir):
    action = InitRepoAction()
    assert action.findFilesMatchingWholename(plain_workdir, 'nonexistent') == []


def test_find_files_matching_wholename_skips_git_dir(tmp_path):
    (tmp_path / '.git').mkdir()
    (tmp_path / '.git' / 'diagram.extra').write_text('should not be found')
    (tmp_path / 'diagram.png').write_bytes(b'\x89PNG')
    action = InitRepoAction()
    matches = action.findFilesMatchingWholename(tmp_path, 'diagram')
    assert matches == ['./diagram.png']


def test_non_comment_lines_skips_percent_prefixed_lines(plain_workdir):
    (plain_workdir / 'commented.tex').write_text(
        "\\input{chapter1}\n% \\input{chapter2}\n  % also skipped\nkept line\n"
    )
    action = InitRepoAction()
    lines = action.nonCommentLines(plain_workdir, 'commented.tex')
    assert lines == ['\\input{chapter1}', 'kept line']


# ---------------------------------------------------------------------------
# Regression: `git diff --unified=0 HEAD~N HEAD` (old->new), not
# `HEAD HEAD~N` (new->old, which inverted added/removed lines - see commit
# d3d252d "Fix reversed diff, dangling paths, and Windows-unsafe project
# listing").
# ---------------------------------------------------------------------------

def test_run_diff_direction_shows_additions_as_plus_lines(tex_git_repo, make_snapshot):
    # tex_git_repo's 2nd commit ("Expand chapter 1") adds a line to
    # chapter1.tex relative to the 1st commit.
    repo = tex_git_repo.repo
    repo.git.reset('--hard', tex_git_repo.shas[1])

    action = InitRepoAction()

    class FakeProject:
        class config:
            concatCommits = 0

    action.init(FakeProject())

    snapshot = make_snapshot(commit_sha=tex_git_repo.shas[1], work_dir=tex_git_repo.path)

    result = action.run(snapshot)

    assert result == SnapshotStatus.COMPLETED
    diff = snapshot.gitDiff.get('chapter1.tex', '')
    assert '+This is an added line.' in diff
    assert '-This is an added line.' not in diff
