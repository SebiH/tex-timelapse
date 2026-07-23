"""Architecture guard: the core pipeline (compiler.py, project.py,
snapshot.py, config.py, actions/**, reporter.py) must never import
flask/flask_socketio. This guards a planned core/ vs api/ split - webserver.py
and the reporters/ implementations are the only places allowed to know about
Flask.

Implemented via AST parsing rather than importing the modules, so this test
can't accidentally trigger Flask import side effects and stays honest even
if a module is (or becomes) hard to import standalone.
"""

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PKG_ROOT = REPO_ROOT / 'tex_timelapse'

FORBIDDEN_MODULES = {'flask', 'flask_socketio'}

CORE_MODULE_PATHS = [
    PKG_ROOT / 'compiler.py',
    PKG_ROOT / 'project.py',
    PKG_ROOT / 'snapshot.py',
    PKG_ROOT / 'config.py',
    PKG_ROOT / 'reporter.py',
    *sorted((PKG_ROOT / 'actions').glob('*.py')),
]


def _top_level_imported_modules(path: Path) -> set:
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                modules.add(node.module.split('.')[0])
    return modules


def test_core_module_paths_is_non_empty():
    # guards against a typo/rename silently making the parametrized test
    # below a no-op
    assert len(CORE_MODULE_PATHS) >= 6
    assert all(p.exists() for p in CORE_MODULE_PATHS)


@pytest.mark.parametrize(
    'module_path', CORE_MODULE_PATHS,
    ids=lambda p: str(p.relative_to(PKG_ROOT)),
)
def test_core_pipeline_module_does_not_import_flask(module_path):
    imported = _top_level_imported_modules(module_path)
    forbidden_hits = imported & FORBIDDEN_MODULES
    assert not forbidden_hits, (
        f'{module_path.relative_to(REPO_ROOT)} imports {forbidden_hits}, '
        'which belong to the API layer (webserver.py / reporters/web_reporter.py)'
    )


def test_webserver_is_the_one_place_allowed_to_import_flask():
    # sanity check that the test above is actually discriminating: the API
    # layer module it's *not* checking does import flask.
    imported = _top_level_imported_modules(PKG_ROOT / 'webserver.py')
    assert 'flask' in imported
