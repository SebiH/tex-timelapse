"""Filesystem locations the rest of the package resolves through, so they
work regardless of the process's current working directory (except where
CWD-relative behaviour is deliberately preserved - see projects_root()).
"""

import os
from pathlib import Path

# The installed package directory, e.g. .../site-packages/tex_timelapse (or
# backend/src/tex_timelapse when running from a checkout via the repo-root
# shim / an editable install).
_PACKAGE_DIR = Path(__file__).resolve().parent


def default_config_path() -> Path:
    """Path to the bundled default_config.yaml, resolved relative to the
    installed package rather than the process's CWD.

    Historically this was read via a literal './default_config.yaml', which
    only worked when the process happened to be launched from the repo root.
    The file now ships *inside* the package (as package data, see
    pyproject.toml) and is resolved right next to this module - so it is
    found no matter what the CWD is, and for both editable installs and a
    real wheel (`pip install ./backend`, as the Docker image does), where
    anything outside the package directory would not be present.
    """
    return _PACKAGE_DIR / 'default_config.yaml'


def projects_root() -> Path:
    """Root directory under which every project lives (`<root>/<slug>/...`).

    Defaults to `./projects`, relative to the process's CWD - identical to
    the previous hardcoded behaviour when the process is launched from the
    repo root (or, in Docker, from /tex-timelapse, per docker-compose.yml's
    volume mounts). Overridable via TEX_TIMELAPSE_PROJECTS_DIR for callers
    that don't want to depend on CWD.
    """
    return Path(os.environ.get('TEX_TIMELAPSE_PROJECTS_DIR', 'projects'))
