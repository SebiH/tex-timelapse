"""Regression tests for tex_timelapse.core.project.Project.list() (see commit
d3d252d): the old implementation derived a project's name from
`file.split('/')[1]` on the glob result, which (a) breaks on Windows path
separators and (b) returns the folder *slug*, not the project's actual
`name` field, whenever the two differ. The fix uses pathlib and reads
`name` out of each project.yaml directly."""

from pathlib import Path

import yaml

from tex_timelapse.core.project import Project


def _write_project_yaml(projects_dir: Path, slug: str, name: str) -> None:
    folder = projects_dir / slug
    folder.mkdir(parents=True)
    with open(folder / 'project.yaml', 'w') as f:
        yaml.dump({'name': name, 'config': {}}, f)


def test_list_returns_display_name_not_folder_slug(isolated_cwd):
    # folder slug deliberately differs from the display name - the old
    # `file.split('/')[1]` code would have returned 'my-cool-project' here.
    _write_project_yaml(isolated_cwd / 'projects', 'my-cool-project', 'My Cool Project!')

    projects = Project.list()

    assert len(projects) == 1
    assert projects[0].name == 'My Cool Project!'


def test_list_finds_multiple_projects(isolated_cwd):
    _write_project_yaml(isolated_cwd / 'projects', 'alpha', 'Alpha')
    _write_project_yaml(isolated_cwd / 'projects', 'beta', 'Beta')

    names = sorted(p.name for p in Project.list())
    assert names == ['Alpha', 'Beta']


def test_list_ignores_yaml_without_a_name(isolated_cwd):
    folder = isolated_cwd / 'projects' / 'no-name'
    folder.mkdir(parents=True)
    with open(folder / 'project.yaml', 'w') as f:
        yaml.dump({'config': {}}, f)  # no 'name' key

    assert Project.list() == []


def test_list_empty_projects_dir_returns_empty_list(isolated_cwd):
    assert Project.list() == []


def test_list_uses_pathlib_glob_not_string_split_on_slash(isolated_cwd):
    # a name containing a literal '/' would defeat any split('/')-based
    # implementation trying to recover it from a path; pathlib + reading
    # project.yaml's own 'name' field must not care.
    _write_project_yaml(isolated_cwd / 'projects', 'a-b-project', 'A/B Project')

    projects = Project.list()
    assert len(projects) == 1
    assert projects[0].name == 'A/B Project'
