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
from tex_timelapse.compiler import compileProject, compileSnapshot
from tex_timelapse.project import Project
from tex_timelapse.snapshot import Snapshot, SnapshotStatus

from .actions.init_repo import InitRepoAction
from .actions.replace_text import ReplaceTextAction
from .actions.compile_latex import CompileLatexAction
from .actions.pdf_to_image import PdfToImageAction
from .actions.assemble_image import AssembleImageAction

class WebServer:
    def __init__(self):
        self.app = Flask(__name__)

        CORS(self.app, resources={r"/*": {"origins": "*"}})
        self.socketio = SocketIO(self.app, cors_allowed_origins='*')

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
                        project.config = request.json['config']
                        project.serialize()
                    # TODO: support name change
                    return jsonify({ 'success': True })

                return jsonify({ 'success': False, 'error': 'No data provided' })
            except Exception as e:
                return jsonify({ 'success': False, 'error': str(e) })


        @self.app.route('/api/projects/<name>/run')
        def __runProject(name):
            try:
                project = Project.deserialize(name)
                project.loadSnapshots()

                jobs = [
                    InitRepoAction(),
                    ReplaceTextAction(),
                    CompileLatexAction(),
                    PdfToImageAction(),
                    AssembleImageAction()
                ]

                compileProject(project, 'test', jobs, WebReporter(self.socketio))

                return { 'success': True }
            except Exception as e:
                return { 'success': False, 'error': str(e) }

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

                jobs = [
                    InitRepoAction(),
                    ReplaceTextAction(),
                    CompileLatexAction(),
                    PdfToImageAction(),
                    AssembleImageAction()
                ]


                if len(matching_snapshot) == 0:
                    return { 'success': False, 'error': 'Snapshot not found' }

                compileSnapshot(project, matching_snapshot[0], jobs, WebReporter(self.socketio))
                Snapshot.serialize(f'{project.projectFolder}/snapshots.yaml', project.snapshots)

                return { 'success': True, 'snapshot': matching_snapshot[0].to_dict() }
            except Exception as e:
                return { 'success': False, 'error': str(e) }


        @self.app.route('/api/projects/<name>/snapshot/<snapshot_sha>/reset/<stage>')
        def __resetSnapshot(name, snapshot_sha, stage):
            try:
                project = Project.deserialize(name)
                project.loadSnapshots()
                matching_snapshot = [s for s in project.snapshots if s.commit_sha == snapshot_sha]

                if len(matching_snapshot) == 0:
                    return { 'success': False, 'error': 'Snapshot not found' }

                snapshot = matching_snapshot[0]

                jobs = [
                    InitRepoAction(),
                    ReplaceTextAction(),
                    CompileLatexAction(),
                    PdfToImageAction(),
                    AssembleImageAction()
                ]

                job_names = [job.getName() for job in jobs]
                # an unknown/missing stage (e.g. the client passed `undefined`)
                # resets every stage, starting from the first
                start_index = job_names.index(stage) if stage in job_names else 0

                for job in jobs[start_index:]:
                    job.init(project)
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

    def run(self):
        self.socketio.run(self.app)
