"""API tests for tex_timelapse.webserver, using Flask's test client - no real
server process, no network. Covers the basic project routes plus the
getImage path-traversal regression (see commit 50eedb0 "Sanitize
user-controlled paths and fix snapshot API responses")."""

import yaml

VALID_SHA = 'a' * 40


def _write_project_yaml(isolated_cwd, slug, name, config=None):
    folder = isolated_cwd / 'projects' / slug
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / 'project.yaml', 'w') as f:
        yaml.dump({'name': name, 'config': config or {}}, f)
    return folder


# ---------------------------------------------------------------------------
# /api/projects
# ---------------------------------------------------------------------------

def test_list_projects_empty(flask_client):
    resp = flask_client.get('/api/projects')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == {'success': True, 'projects': []}


def test_list_projects_returns_display_names(flask_client, isolated_cwd):
    _write_project_yaml(isolated_cwd, 'my-project', 'My Project')

    resp = flask_client.get('/api/projects')
    data = resp.get_json()
    assert data['success'] is True
    assert data['projects'] == ['My Project']


# ---------------------------------------------------------------------------
# /api/projects/<name> GET/POST
# ---------------------------------------------------------------------------

def test_get_project_not_found_returns_success_false(flask_client):
    resp = flask_client.get('/api/projects/does-not-exist')
    data = resp.get_json()
    assert data['success'] is False
    assert 'error' in data


def test_get_project_returns_config_and_snapshots(flask_client, isolated_cwd, project_factory):
    project_factory(name='Real Project')

    resp = flask_client.get('/api/projects/Real%20Project')
    data = resp.get_json()
    assert data['success'] is True
    assert data['project']['name'] == 'Real Project'
    assert len(data['project']['snapshots']) == 4  # tex_git_repo has 4 commits


def test_post_project_updates_config_and_persists(flask_client, isolated_cwd, project_factory):
    project_factory(name='Editable Project', config_overrides={'rows': 2, 'columns': 3})

    resp = flask_client.post('/api/projects/Editable%20Project', json={'config': {'rows': 9}})
    assert resp.get_json() == {'success': True}

    project_yaml_path = isolated_cwd / 'projects' / 'editable-project' / 'project.yaml'
    with open(project_yaml_path) as f:
        saved = yaml.safe_load(f)

    # the posted field changed...
    assert int(saved['config']['rows']) == 9
    # ...but an untouched field must survive (partial edits shouldn't reset
    # the rest of the config back to global defaults)
    assert int(saved['config']['columns']) == 3


def test_post_project_without_json_body_reports_failure(flask_client, isolated_cwd, project_factory):
    project_factory(name='No Body Project')
    resp = flask_client.post('/api/projects/No%20Body%20Project')
    data = resp.get_json()
    assert data['success'] is False


# ---------------------------------------------------------------------------
# getImage: path traversal regression (commit 50eedb0)
# ---------------------------------------------------------------------------

def test_get_image_happy_path_returns_200(flask_client, isolated_cwd):
    _write_project_yaml(isolated_cwd, 'img-project', 'Img Project')
    thumb_dir = isolated_cwd / 'projects' / 'img-project' / 'thumbnails' / VALID_SHA
    thumb_dir.mkdir(parents=True)
    (thumb_dir / 'page-01.jpg').write_bytes(b'\xff\xd8\xff fake-jpeg')

    resp = flask_client.get(f'/api/projects/Img%20Project/snapshot/{VALID_SHA}/image/page-01.jpg')
    assert resp.status_code == 200


def test_get_image_rejects_invalid_sha_format(flask_client, isolated_cwd):
    _write_project_yaml(isolated_cwd, 'img-project', 'Img Project')

    resp = flask_client.get('/api/projects/Img%20Project/snapshot/not-a-sha/image/page-01.jpg')
    assert resp.status_code == 404


def test_get_image_rejects_dotdot_in_sha(flask_client, isolated_cwd):
    _write_project_yaml(isolated_cwd, 'img-project', 'Img Project')

    resp = flask_client.get('/api/projects/Img%20Project/snapshot/..%2f..%2fetc/image/page-01.jpg')
    assert resp.status_code == 404


def test_get_image_rejects_dotdot_in_image_name(flask_client, isolated_cwd):
    _write_project_yaml(isolated_cwd, 'img-project', 'Img Project')
    thumb_dir = isolated_cwd / 'projects' / 'img-project' / 'thumbnails' / VALID_SHA
    thumb_dir.mkdir(parents=True)
    (thumb_dir / 'page-01.jpg').write_bytes(b'real thumbnail')

    # image traversal attempt reaching for a project.yaml one level up
    resp = flask_client.get(f'/api/projects/Img%20Project/snapshot/{VALID_SHA}/image/..%2f..%2fproject.yaml')
    assert resp.status_code == 404


def test_get_image_rejects_absolute_path_in_image_name(flask_client, isolated_cwd):
    _write_project_yaml(isolated_cwd, 'img-project', 'Img Project')

    # an absolute path masquerading as a single path segment - '/' isn't in
    # the allowed image charset, so this must be rejected regardless of
    # whether Flask's own routing already refuses to match it.
    resp = flask_client.get(f'/api/projects/Img%20Project/snapshot/{VALID_SHA}/image/%2Fetc%2Fpasswd')
    assert resp.status_code == 404


def test_get_image_rejects_unknown_project(flask_client):
    resp = flask_client.get(f'/api/projects/does-not-exist/snapshot/{VALID_SHA}/image/page-01.jpg')
    assert resp.status_code == 404


def test_get_image_rejects_missing_file_for_valid_sha(flask_client, isolated_cwd):
    _write_project_yaml(isolated_cwd, 'img-project', 'Img Project')
    (isolated_cwd / 'projects' / 'img-project' / 'thumbnails' / VALID_SHA).mkdir(parents=True)

    resp = flask_client.get(f'/api/projects/Img%20Project/snapshot/{VALID_SHA}/image/does-not-exist.jpg')
    assert resp.status_code == 404
