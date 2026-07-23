"""API tests for tex_timelapse.webserver, using Flask's test client - no real
server process, no network. Covers the basic project routes, the async job
endpoints, plus the getImage path-traversal regression (see commit 50eedb0
"Sanitize user-controlled paths and fix snapshot API responses")."""

import pytest
import yaml

import tex_timelapse.webserver as webserver_mod

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
# async job endpoints: POST /api/projects/<name>/jobs, GET/DELETE /api/jobs/<id>
# ---------------------------------------------------------------------------

@pytest.fixture
def job_server(isolated_cwd):
    """A WebServer + test client. start_background_task is NOT auto-run here;
    each test decides whether the render body executes, so it can observe a
    job while it is still RUNNING."""
    from tex_timelapse.webserver import WebServer

    server = WebServer()
    server.app.testing = True
    with server.app.test_client() as client:
        yield server, client


def test_start_job_returns_202_with_job_id(job_server, project_factory, monkeypatch):
    server, client = job_server
    project_factory(name='Job Project')
    # run the background task synchronously so the job completes deterministically
    monkeypatch.setattr(server.socketio, 'start_background_task',
                        lambda fn, *a, **k: fn(*a, **k))
    # no-op render: we're testing the endpoint wiring, not the pipeline
    monkeypatch.setattr(webserver_mod, 'compileProject', lambda *a, **k: None)

    resp = client.post('/api/projects/Job%20Project/jobs', json={'output': 'vid'})
    assert resp.status_code == 202
    data = resp.get_json()
    assert data['success'] is True
    assert data['job']['output'] == 'vid'
    # NB: because start_background_task is patched to run synchronously here,
    # the render already finished before the response was built, so the
    # POST-time status is not asserted (it would be 'running' only under real
    # async execution). Poll instead.
    poll = client.get(f"/api/jobs/{data['job']['id']}")
    assert poll.status_code == 200
    assert poll.get_json()['job']['status'] == 'completed'


def test_start_job_unknown_project_returns_404(job_server):
    _server, client = job_server
    resp = client.post('/api/projects/nope/jobs', json={})
    assert resp.status_code == 404
    assert resp.get_json()['success'] is False


def test_second_concurrent_job_for_same_project_returns_409(job_server, project_factory, monkeypatch):
    server, client = job_server
    project_factory(name='Busy Project')
    # never actually run the render, so the first job stays RUNNING
    monkeypatch.setattr(server.socketio, 'start_background_task', lambda fn, *a, **k: None)
    monkeypatch.setattr(webserver_mod, 'compileProject', lambda *a, **k: None)

    first = client.post('/api/projects/Busy%20Project/jobs', json={})
    assert first.status_code == 202

    second = client.post('/api/projects/Busy%20Project/jobs', json={})
    assert second.status_code == 409
    assert second.get_json()['success'] is False


def test_get_unknown_job_returns_404(job_server):
    _server, client = job_server
    resp = client.get('/api/jobs/does-not-exist')
    assert resp.status_code == 404


def test_delete_job_requests_cancel(job_server, project_factory, monkeypatch):
    server, client = job_server
    project_factory(name='Cancel Project')
    monkeypatch.setattr(server.socketio, 'start_background_task', lambda fn, *a, **k: None)
    monkeypatch.setattr(webserver_mod, 'compileProject', lambda *a, **k: None)

    started = client.post('/api/projects/Cancel%20Project/jobs', json={})
    job_id = started.get_json()['job']['id']

    resp = client.delete(f'/api/jobs/{job_id}')
    assert resp.status_code == 202
    # the cooperative cancel flag is now set on the live job
    assert server.jobs.get(job_id).cancel_requested is True


def test_delete_unknown_job_returns_404(job_server):
    _server, client = job_server
    resp = client.delete('/api/jobs/does-not-exist')
    assert resp.status_code == 404


def test_job_ends_cancelled_when_render_was_cancelled(job_server, project_factory, monkeypatch):
    # a render whose cancel flag was set before it finished must end CANCELLED,
    # not COMPLETED.
    server, client = job_server
    project_factory(name='CancelEnd Project')

    def fake_compile(project, output, actions, reporter, should_cancel=None):
        # emulate a cooperative stop: the job was cancelled mid-flight
        assert should_cancel is not None

    monkeypatch.setattr(webserver_mod, 'compileProject', fake_compile)

    # start_background_task: set the cancel flag, then run the render body -
    # mimicking a DELETE that landed while the render was in progress.
    def _cancel_then_run(fn, *a, **k):
        job = list(server.jobs._jobs.values())[-1]
        job.request_cancel()
        fn(*a, **k)

    monkeypatch.setattr(server.socketio, 'start_background_task', _cancel_then_run)

    started = client.post('/api/projects/CancelEnd%20Project/jobs', json={})
    job_id = started.get_json()['job']['id']
    assert client.get(f'/api/jobs/{job_id}').get_json()['job']['status'] == 'cancelled'


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
