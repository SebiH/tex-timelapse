from os import path
import os
import re
from shutil import rmtree
from flask import Flask, jsonify, send_file
from flask import request
from flask_socketio import SocketIO # type: ignore
from flask_cors import CORS
from werkzeug.utils import secure_filename

from tex_timelapse.reporters.web_reporter import WebReporter
from tex_timelapse.reporters.job_reporter import JobReporter
from tex_timelapse.core.compiler import compileProject, compileSnapshot
from tex_timelapse.api.jobs import JobManager, JobStatus
from tex_timelapse.core.project import Project
from tex_timelapse.core.snapshot import Snapshot, SnapshotStatus
from tex_timelapse.core.config import Config

from tex_timelapse.core.actions import create_and_init_actions, get_stage_names

# Browser origins allowed to call the API / open the Socket.IO connection.
# Overridable via TEX_TIMELAPSE_CORS_ORIGINS (comma-separated) for other
# deployments; defaults to the Vite dev server. The API used to allow '*',
# which lets any web page a user visits drive their local server.
_DEFAULT_CORS_ORIGINS = ['http://localhost:5173', 'http://127.0.0.1:5173']


def _cors_origins() -> list[str]:
    raw = os.environ.get('TEX_TIMELAPSE_CORS_ORIGINS', '')
    origins = [o.strip() for o in raw.split(',') if o.strip()]
    return origins or _DEFAULT_CORS_ORIGINS


class WebServer:
    def __init__(self):
        self.app = Flask(__name__)

        origins = _cors_origins()
        CORS(self.app, resources={r"/*": {"origins": origins}})
        self.socketio = SocketIO(self.app, cors_allowed_origins=origins)
        self.jobs = JobManager()

        @self.app.route('/api/projects')
        def listProjects():
            try:
                return {"success": True, "projects": [p.name for p in Project.list()]}
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.app.route('/api/projects/<name>', methods=['GET'])
        def __getProject(name):
            try :
                project = Project.deserialize(name)
                project_dict = project.to_dict()
                project.loadSnapshots()
                project_dict['snapshots'] = [snapshot.to_dict() for snapshot in project.snapshots]
                return { 'success': True, 'project': project_dict }
            except Exception as e:
                return { 'success': False, 'error': str(e) }

        @self.app.route('/api/projects/<name>', methods=['POST'])
        def __setProject(name):
            try:
                project = Project.deserialize(name)
                if request.json:
                    if 'config' in request.json:
                        # missing fields in the posted config fall back to
                        # the project's current values, not the global
                        # defaults - a partial edit shouldn't reset
                        # untouched fields.
                        project.config = Config.from_dict(request.json['config'], defaults=project.config.to_dict())
                        project.serialize()
                    # TODO: support name change
                    return jsonify({ 'success': True })

                return jsonify({ 'success': False, 'error': 'No data provided' })
            except Exception as e:
                return jsonify({ 'success': False, 'error': str(e) })


        @self.app.route('/api/projects/<name>/jobs', methods=['POST'])
        def __startJob(name):
            # Start a render on a background task and return immediately with a
            # job id. Replaces the old GET /run, which blocked a request thread
            # for the entire (minutes-long) compile+encode.
            try:
                project = Project.deserialize(name)
                project.loadSnapshots()
            except Exception as e:
                return { 'success': False, 'error': str(e) }, 404

            body = request.get_json(silent=True) or {}
            output = body.get('output', 'output')

            try:
                job = self.jobs.create(name, output)
            except RuntimeError as e:
                # a render is already running for this project
                return { 'success': False, 'error': str(e) }, 409

            actions = create_and_init_actions(project)
            reporter = JobReporter(self.socketio, job)

            def _run(job_id):
                try:
                    compileProject(project, output, actions, reporter,
                                   should_cancel=lambda: job.cancel_requested)
                    status = JobStatus.CANCELLED if job.cancel_requested else JobStatus.COMPLETED
                    self.jobs.finish(job_id, status)
                except Exception as e:
                    reporter.log(f'Render failed: {e}')
                    self.jobs.finish(job_id, JobStatus.FAILED, str(e))

            self.socketio.start_background_task(_run, job.id)
            return { 'success': True, 'job': job.to_dict() }, 202

        @self.app.route('/api/jobs/<job_id>', methods=['GET'])
        def __getJob(job_id):
            job = self.jobs.get(job_id)
            if job is None:
                return { 'success': False, 'error': 'Job not found' }, 404
            return { 'success': True, 'job': job.to_dict() }

        @self.app.route('/api/jobs/<job_id>', methods=['DELETE'])
        def __cancelJob(job_id):
            job = self.jobs.get(job_id)
            if job is None:
                return { 'success': False, 'error': 'Job not found' }, 404
            job.request_cancel()
            # cooperative: the render stops before its next snapshot / encode.
            return { 'success': True, 'job': job.to_dict() }, 202

        @self.app.route('/api/projects/<name>/reset')
        def __resetProject(name):
            try:
                project = Project.deserialize(name)

                # todo: handle this in a more central location
                rmtree(f'{project.projectFolder}/frames', ignore_errors=True)
                rmtree(f'{project.projectFolder}/thumbnails', ignore_errors=True)
                if os.path.exists(f'{project.projectFolder}/snapshots.yaml'):
                    os.remove(f'{project.projectFolder}/snapshots.yaml')

                return { 'success': True }
            except Exception as e:
                return { 'success': False, 'error': str(e) }


        @self.app.route('/api/projects/<name>/snapshot/<snapshot_sha>/run')
        def __compileSnapshot(name, snapshot_sha):
            try:
                project = Project.deserialize(name)
                project.loadSnapshots()
                matching_snapshot = [s for s in project.snapshots if s.commit_sha == snapshot_sha]

                jobs = create_and_init_actions(project)

                if len(matching_snapshot) == 0:
                    return { 'success': False, 'error': 'Snapshot not found' }

                compileSnapshot(project, matching_snapshot[0], jobs, WebReporter(self.socketio))
                Snapshot.serialize(f'{project.projectFolder}/snapshots.yaml', project.snapshots)

                return { 'success': True, 'snapshot': matching_snapshot[0].to_dict() }
            except Exception as e:
                return { 'success': False, 'error': str(e) }


        @self.app.route('/api/projects/<name>/snapshot/<snapshot_sha>/reset')
        @self.app.route('/api/projects/<name>/snapshot/<snapshot_sha>/reset/<stage>')
        def __resetSnapshot(name, snapshot_sha, stage=None):
            try:
                project = Project.deserialize(name)
                project.loadSnapshots()
                matching_snapshot = [s for s in project.snapshots if s.commit_sha == snapshot_sha]

                if len(matching_snapshot) == 0:
                    return { 'success': False, 'error': 'Snapshot not found' }

                snapshot = matching_snapshot[0]

                jobs = create_and_init_actions(project)

                job_names = get_stage_names()
                # an unknown/missing stage (e.g. the client passed `undefined`)
                # resets every stage, starting from the first
                start_index = job_names.index(stage) if stage in job_names else 0

                for job in jobs[start_index:]:
                    job.reset(snapshot)
                    snapshot.jobs.pop(job.getName(), None)

                snapshot.status = SnapshotStatus.PENDING
                snapshot.error = ''

                Snapshot.serialize(f'{project.projectFolder}/snapshots.yaml', project.snapshots)

                return { 'success': True, 'snapshot': snapshot.to_dict() }
            except Exception as e:
                return { 'success': False, 'error': str(e) }


        @self.app.route('/api/projects/<name>/snapshot/<snapshot>/image/<image>')
        def getImage(name, snapshot, image):
            # sanitize: a commit sha and a plain image basename only - no path
            # separators or traversal sequences are allowed through.
            if not re.fullmatch(r'[0-9a-f]{7,40}', snapshot):
                return jsonify({ 'success': False, 'error': 'Invalid snapshot' }), 404

            if not re.fullmatch(r'[A-Za-z0-9._-]+', image) or '..' in image:
                return jsonify({ 'success': False, 'error': 'Invalid image' }), 404

            try:
                project = Project.deserialize(name)
            except Exception as e:
                return jsonify({ 'success': False, 'error': str(e) }), 404

            thumbnails_dir = path.realpath(path.join(os.getcwd(), project.projectFolder, 'thumbnails'))
            filePath = path.realpath(path.join(thumbnails_dir, snapshot, image))

            # ensure the resolved path didn't escape the project's thumbnails dir
            if filePath != thumbnails_dir and not filePath.startswith(thumbnails_dir + os.sep):
                return jsonify({ 'success': False, 'error': 'Invalid path' }), 404

            if not os.path.isfile(filePath):
                return jsonify({ 'success': False, 'error': 'Not found' }), 404

            return send_file(filePath)


        UPLOAD_FOLDER = 'uploads'
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)


        @self.app.route('/api/import', methods=['POST'])
        def __import_project():
            if 'file' not in request.files:
                return jsonify({"error": "No file part"}), 400

            project_file = request.files['file']
            project_name = request.form.get('name', '')

            if project_file.filename == '':
                return jsonify({"error": "No selected file"}), 400

            if not project_file.filename.endswith('.zip'):
                return jsonify({"error": "Only zip files are allowed"}), 400

            if not project_name:
                return jsonify({"error": "Project name is required"}), 400

            # Save the file to the upload folder
            filename = secure_filename(project_file.filename)
            if not filename:
                return jsonify({"error": "Invalid file name"}), 400

            file_path = os.path.join(UPLOAD_FOLDER, filename)
            project_file.save(file_path)

            project = Project.create(project_name, f'{UPLOAD_FOLDER}/{filename}')

            # remove the uploaded file
            os.remove(file_path)

            project.loadSnapshots()

            return jsonify(
                {
                    "message": "Project imported successfully",
                    "project": project.to_dict()
                }
            ), 200

    def send_message(self, message):
        self.socketio.emit('message', message)

    def run(self, host: str = '127.0.0.1', port: int = 5000):
        # Flask-SocketIO defaults to 127.0.0.1, which is unreachable from
        # outside a container. The default stays loopback-only so running the
        # server on a workstation does not silently expose it to the network;
        # the Docker image passes --host 0.0.0.0 explicitly.
        #
        # allow_unsafe_werkzeug=True: with no eventlet/gevent installed,
        # Flask-SocketIO >=5 falls back to the Werkzeug dev server and then
        # refuses to start without this flag. tex-timelapse is a single-user
        # local/containerised tool, not a public production server, and the
        # dev server is exactly what it wants - so opt in explicitly rather
        # than crash on startup.
        self.socketio.run(self.app, host=host, port=port, allow_unsafe_werkzeug=True)
