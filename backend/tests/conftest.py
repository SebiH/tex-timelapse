"""Shared fixtures for the tex-timelapse backend test suite.

Nothing here should ever write into the repo's real `./projects` directory.
Any fixture that constructs a `Project` chdirs into a pytest-managed
`tmp_path` first (via `isolated_cwd`) so `Project.projectFolder`'s hardcoded
`./projects/<slug>` resolves under the temp dir instead.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import shutil

import git
import pytest
import yaml
from slugify import slugify

from tex_timelapse.core.config import Config
from tex_timelapse.core.project import Project
from tex_timelapse.core.reporter import Reporter
from tex_timelapse.core.snapshot import Snapshot

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / 'default_config.yaml'


# ---------------------------------------------------------------------------
# LaTeX fixture content
# ---------------------------------------------------------------------------

MAIN_TEX_V1 = (
    "\\documentclass{article}\n"
    "\\usepackage{graphicx}\n"
    "\\addbibresource{refs.bib}\n"
    "\\begin{document}\n"
    "\\input{chapter1}\n"
    "\\includegraphics{diagram}\n"
    "\\end{document}\n"
)

MAIN_TEX_V2 = (
    "\\documentclass{article}\n"
    "\\usepackage{graphicx}\n"
    "\\addbibresource{refs.bib}\n"
    "\\begin{document}\n"
    "\\input{chapter1}\n"
    "\\include{chapter2}\n"
    "\\includegraphics{diagram}\n"
    "\\end{document}\n"
)

CHAPTER1_V1 = "Hello world.\n"
CHAPTER1_V2 = "Hello world.\nThis is an added line.\n"

CHAPTER2_V1 = "Chapter two content.\n"
CHAPTER2_V2 = "Chapter two content.\nRevised line.\n"

BIB_V1 = (
    "@misc{example,\n"
    "  title = {Example},\n"
    "  author = {Someone},\n"
    "}\n"
)

# a 1x1 PNG, just enough to exist as a file \\includegraphics can "find"
DIAGRAM_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
    "5305000000097048597300000ec300000ec301c76fa864000000174944415478"
    "9c6360606060646000000005000101a5f645400000000049454e44ae426082"
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


@dataclass
class TexGitRepo:
    """A tiny throwaway multi-commit LaTeX project, backed by a real git
    repository on disk."""
    path: Path
    shas: List[str] = field(default_factory=list)

    @property
    def repo(self) -> git.Repo:
        return git.Repo(self.path)


@pytest.fixture
def tex_git_repo(tmp_path_factory) -> TexGitRepo:
    """Build a tiny git repo with a multi-commit LaTeX project:

    1. Initial commit: main.tex (\\input, \\addbibresource, \\includegraphics),
       chapter1.tex, refs.bib, diagram.png.
    2. chapter1.tex gains a line.
    3. chapter2.tex is added and \\include'd from main.tex.
    4. chapter2.tex gains a line.

    Returns a TexGitRepo with `.path` (the repo's working directory) and
    `.shas` (commit hashes, oldest first).
    """
    repo_dir = tmp_path_factory.mktemp('tex-source')
    repo = git.Repo.init(repo_dir)
    with repo.config_writer() as cw:
        cw.set_value('user', 'name', 'Test User')
        cw.set_value('user', 'email', 'test@example.com')

    shas = []

    _write(repo_dir / 'main.tex', MAIN_TEX_V1)
    _write(repo_dir / 'chapter1.tex', CHAPTER1_V1)
    _write(repo_dir / 'refs.bib', BIB_V1)
    (repo_dir / 'diagram.png').write_bytes(DIAGRAM_PNG_BYTES)
    repo.index.add(['main.tex', 'chapter1.tex', 'refs.bib', 'diagram.png'])
    shas.append(repo.index.commit('Initial commit').hexsha)

    _write(repo_dir / 'chapter1.tex', CHAPTER1_V2)
    repo.index.add(['chapter1.tex'])
    shas.append(repo.index.commit('Expand chapter 1').hexsha)

    _write(repo_dir / 'chapter2.tex', CHAPTER2_V1)
    _write(repo_dir / 'main.tex', MAIN_TEX_V2)
    repo.index.add(['chapter2.tex', 'main.tex'])
    shas.append(repo.index.commit('Add chapter 2').hexsha)

    _write(repo_dir / 'chapter2.tex', CHAPTER2_V2)
    repo.index.add(['chapter2.tex'])
    shas.append(repo.index.commit('Revise chapter 2').hexsha)

    return TexGitRepo(path=repo_dir, shas=shas)


# ---------------------------------------------------------------------------
# Isolation: never touch the real ./projects
# ---------------------------------------------------------------------------

@pytest.fixture
def isolated_cwd(tmp_path, monkeypatch) -> Path:
    """Chdir into a throwaway directory and give it its own `projects/` and
    `default_config.yaml`, so every relative path in project.py/compiler.py
    (`./projects/<slug>`, `./default_config.yaml`) resolves under tmp_path -
    never under the repo's real `projects/`."""
    (tmp_path / 'projects').mkdir()
    if DEFAULT_CONFIG_PATH.exists():
        shutil.copy(DEFAULT_CONFIG_PATH, tmp_path / 'default_config.yaml')
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def project_factory(isolated_cwd, tex_git_repo):
    """Factory fixture: build a Project rooted under `isolated_cwd`, with its
    `source/` populated from a copy of `tex_git_repo`'s `.git` directory
    (mirroring what `compiler.initFolder` does with a real project - only
    the `.git` dir is needed, `git reset --hard` recreates the working tree).

    Returns a callable `(name=..., config_overrides=...) -> Project`.
    """
    def _make(name: str = 'Test Project', config_overrides: Optional[dict] = None) -> Project:
        slug = slugify(name)
        project_folder = isolated_cwd / 'projects' / slug
        source_dir = project_folder / 'source'
        source_dir.mkdir(parents=True)
        shutil.copytree(tex_git_repo.path / '.git', source_dir / '.git')

        config_dict = {
            'rows': 1,
            'columns': 1,
            'workers': 1,
            'concatCommits': 0,
            'highlightChanges': False,
        }
        if config_overrides:
            config_dict.update(config_overrides)

        project_yaml = {'name': name, 'config': config_dict}
        with open(project_folder / 'project.yaml', 'w') as f:
            yaml.dump(project_yaml, f)

        return Project.deserialize(name)

    return _make


@pytest.fixture
def plain_workdir(tmp_path) -> Path:
    """A directory laid out like a snapshot's workdir, populated directly
    (no git involved) - handy for testing pure file-scanning helpers such as
    InitRepoAction's include resolution."""
    _write(tmp_path / 'main.tex', MAIN_TEX_V2)
    _write(tmp_path / 'chapter1.tex', CHAPTER1_V1)
    _write(tmp_path / 'chapter2.tex', CHAPTER2_V1)
    _write(tmp_path / 'refs.bib', BIB_V1)
    (tmp_path / 'diagram.png').write_bytes(DIAGRAM_PNG_BYTES)
    return tmp_path


@pytest.fixture
def make_snapshot():
    """Factory for a bare Snapshot with its workdir already set."""
    def _make(commit_sha: str = 'deadbeef', index: int = 0, work_dir: Optional[Path] = None) -> Snapshot:
        snapshot = Snapshot(commit_sha, 1700000000, index)
        if work_dir is not None:
            snapshot.setWorkDir(str(work_dir))
        return snapshot
    return _make


class RecordingReporter(Reporter):
    """No-op Reporter that records every call, for asserting on pipeline
    behaviour without a real terminal/socket sink."""
    def __init__(self) -> None:
        self.stages: List[tuple] = []
        self.logs: List[str] = []
        self.progress: List[float] = []
        self.updates: List[Snapshot] = []
        self.added: List[Snapshot] = []

    def set_stage(self, name: str, length: int) -> None:
        self.stages.append((name, length))

    def add_progress(self, snapshot: Snapshot) -> None:
        self.added.append(snapshot)

    def update_progress(self, snapshot: Snapshot) -> None:
        self.updates.append(snapshot)

    def set_progress(self, num: float) -> None:
        self.progress.append(num)

    def log(self, msg: str, snapshot: Optional[Snapshot] = None) -> None:
        self.logs.append(msg)


@pytest.fixture
def recording_reporter() -> RecordingReporter:
    return RecordingReporter()


@pytest.fixture
def flask_client(isolated_cwd):
    """A Flask test client for WebServer's app, constructed after chdir'ing
    into an isolated tmp dir (WebServer.__init__ creates an `uploads/`
    directory relative to CWD as a side effect)."""
    from tex_timelapse.api.server import WebServer

    server = WebServer()
    server.app.testing = True
    with server.app.test_client() as client:
        yield client
