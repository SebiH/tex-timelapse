"""Regression tests for tex_timelapse.compiler, guarding two previously-fixed
defects (see commit ec8f827 "Fix pipeline submitting zero snapshots with
default config"):

1. With the shipped default `concatCommits: 0`, every snapshot must actually
   be submitted for compilation - the old loop condition
   `retry_count < concat_commits // 2 or concat_commits == -1` was False on
   the very first iteration whenever concatCommits was 0, so nothing was
   ever submitted and ffmpeg silently encoded an empty/stale frame set.
2. A snapshot pipeline failure (an exception escaping compileSnapshot) must
   propagate out of compileProject instead of being swallowed by a bare
   `print(e)` and falling through to encode a partial/wrong video.

Both tests fake compileSnapshot and FfmpegProgress directly - no git, LaTeX
or ffmpeg involved.
"""

from pathlib import Path

import pytest

import tex_timelapse.compiler as compiler
from tex_timelapse.config import Config
from tex_timelapse.project import Project
from tex_timelapse.snapshot import Snapshot, SnapshotStatus


class FakeFfmpegProgress:
    """Records whether it was ever constructed/run - a real invocation would
    require the ffmpeg binary and real input frames."""
    instances = []

    def __init__(self, cmd):
        self.cmd = cmd
        FakeFfmpegProgress.instances.append(self)

    def run_command_with_progress(self):
        return iter([])


@pytest.fixture(autouse=True)
def _reset_fake_ffmpeg():
    FakeFfmpegProgress.instances = []
    yield
    FakeFfmpegProgress.instances = []


@pytest.fixture
def bare_project(tmp_path) -> Project:
    """A Project with no on-disk source/config - just enough state for
    compileProject to run against (projectFolder, config, snapshots)."""
    project = Project('Regression Test')
    project.projectFolder = str(tmp_path / 'proj')
    Path(project.projectFolder).mkdir(parents=True)
    project.config = Config(workers=1, concatCommits=0, framerate=8, videoscale=0.25)
    project.snapshots = [Snapshot(f'sha{i}', 1700000000, i) for i in range(4)]
    return project


def test_concat_commits_zero_submits_every_snapshot(bare_project, recording_reporter, monkeypatch):
    submitted = []

    def fake_compile_snapshot(project, snapshot, actions, reporter):
        submitted.append(snapshot.commit_sha)
        snapshot.status = SnapshotStatus.COMPLETED
        return snapshot

    monkeypatch.setattr(compiler, 'compileSnapshot', fake_compile_snapshot)
    monkeypatch.setattr(compiler, 'FfmpegProgress', FakeFfmpegProgress)

    compiler.compileProject(bare_project, 'out', actions=[], reporter=recording_reporter)

    # the actual regression: with concatCommits=0 every snapshot must be
    # submitted exactly once (the old code submitted zero).
    assert sorted(submitted) == sorted(s.commit_sha for s in bare_project.snapshots)
    assert len(submitted) == len(bare_project.snapshots)

    # and the run proceeds to "encode" (our fake) afterwards
    assert len(FakeFfmpegProgress.instances) == 1

    # snapshots.yaml was written
    assert (Path(bare_project.projectFolder) / 'snapshots.yaml').exists()


def test_concat_commits_negative_one_also_submits_every_snapshot(bare_project, recording_reporter, monkeypatch):
    # -1 is the shipped Config default (see Config.workers/concatCommits
    # docstring) and must behave the same as 0: no concatenation.
    bare_project.config.concatCommits = -1
    submitted = []

    def fake_compile_snapshot(project, snapshot, actions, reporter):
        submitted.append(snapshot.commit_sha)
        snapshot.status = SnapshotStatus.COMPLETED
        return snapshot

    monkeypatch.setattr(compiler, 'compileSnapshot', fake_compile_snapshot)
    monkeypatch.setattr(compiler, 'FfmpegProgress', FakeFfmpegProgress)

    compiler.compileProject(bare_project, 'out', actions=[], reporter=recording_reporter)

    assert len(submitted) == len(bare_project.snapshots)


def test_compile_project_reraises_on_snapshot_failure_instead_of_encoding(bare_project, recording_reporter, monkeypatch):
    def failing_compile_snapshot(project, snapshot, actions, reporter):
        raise RuntimeError('boom: pipeline stage exploded')

    monkeypatch.setattr(compiler, 'compileSnapshot', failing_compile_snapshot)
    monkeypatch.setattr(compiler, 'FfmpegProgress', FakeFfmpegProgress)

    with pytest.raises(RuntimeError, match='boom'):
        compiler.compileProject(bare_project, 'out', actions=[], reporter=recording_reporter)

    # the old behaviour printed the error and fell through to ffmpeg anyway;
    # the fix must stop before ever constructing FfmpegProgress.
    assert FakeFfmpegProgress.instances == []
    # and the reporter should have heard about it (reporter.log, not print)
    assert any('boom' in msg for msg in recording_reporter.logs)


def test_compile_project_cleans_up_workdir_even_on_failure(bare_project, recording_reporter, monkeypatch):
    workdir = Path(bare_project.projectFolder) / 'workdir'
    workdir.mkdir(parents=True)
    (workdir / 'marker').write_text('leftover')

    def failing_compile_snapshot(project, snapshot, actions, reporter):
        raise RuntimeError('boom')

    monkeypatch.setattr(compiler, 'compileSnapshot', failing_compile_snapshot)
    monkeypatch.setattr(compiler, 'FfmpegProgress', FakeFfmpegProgress)

    with pytest.raises(RuntimeError):
        compiler.compileProject(bare_project, 'out', actions=[], reporter=recording_reporter)

    assert not workdir.exists()
