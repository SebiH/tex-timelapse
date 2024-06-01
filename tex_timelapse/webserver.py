from os import path
import os
from shutil import rmtree
from flask import Flask, jsonify, send_file
from flask import request
from flask_socketio import SocketIO # type: ignore
from flask_cors import CORS # type: ignore

from tex_timelapse.reporters.web_reporter import WebReporter
from tex_timelapse.compiler import compileProject, compileSnapshot
from tex_timelapse.project import Project, init_project, list_projects
from tex_timelapse.util.serialization import saveToFile, saveToFileTmp

from .actions.init_repo import InitRepoAction
from .actions.compile_latex import CompileLatexAction
from .actions.pdf_to_image import PdfToImageAction
from .actions.assemble_image import AssembleImageAction

class WebServer:
    def __init__(self):
        self.app = Flask(__name__)

        CORS(self.app, resources={r"/*": {"origins": "*"}})
        self.socketio = SocketIO(self.app, cors_allowed_origins='*')

        webProjects = {}
        localProjects: dict[str, Project] = {}
        self.init_projects(webProjects, localProjects)


        @self.app.route('/api/projects')
        def listProjects():
            return list(webProjects.keys())

        @self.app.route('/api/projects/<name>', methods=['GET'])
        def __getProject(name):
            return webProjects[name]

        @self.app.route('/api/projects/<name>', methods=['POST'])
        def __setProject(name):
            project = localProjects[name]
            if request.json:
                if 'config' in request.json:
                    project.config = request.json['config']
                    webProjects[name]['config'] = project.config
                    saveToFileTmp(f'{project.projectFolder}/project.yaml', project.config)
                if 'name' in request.json and request.json['name'] != name:
                    newName = request.json['name']
                    os.rename(project.projectFolder, f'./projects/{newName}')
                    project.name = newName
                    project.projectFolder = f'./projects/{newName}'

                    webProjects[newName] = webProjects.pop(name)
                    localProjects[newName] = localProjects.pop(name)

                return jsonify({ 'success': True })

            return jsonify({ 'success': False, 'error': 'No data provided' })


        @self.app.route('/api/projects/<name>/run')
        def __runProject(name):
            project = localProjects[name]
            try:
                jobs = [
                    InitRepoAction(),
                    CompileLatexAction(),
                    PdfToImageAction(),
                    AssembleImageAction()
                ]

                compileProject(project, 'test', jobs, WebReporter(self.socketio))

                # update snapshot in project snapshots
                project.initSnapshots()
                webProjects[name]['snapshots'] = [snapshot.to_dict() for snapshot in project.snapshots]

                return { 'success': True }
            except Exception as e:
                return { 'success': False, 'error': str(e) }

        @self.app.route('/api/projects/<name>/reset')
        def __resetProject(name):
            project = localProjects[name]
            try:
                rmtree(f'{project.projectFolder}/snapshots', ignore_errors=True)
                project.initSnapshots()
                webProjects[name]['snapshots'] = [snapshot.to_dict() for snapshot in project.snapshots]
                return { 'success': True, 'snapshots': webProjects[name]['snapshots'] }
            except Exception as e:
                return { 'success': False, 'error': str(e) }

        @self.app.route('/api/projects/<name>/snapshot/<snapshot_sha>/run')
        def __compileSnapshot(name, snapshot_sha):
            project = localProjects[name]
            try:
                jobs = [
                    InitRepoAction(),
                    CompileLatexAction(),
                    PdfToImageAction(),
                    AssembleImageAction()
                ]

                snapshot = compileSnapshot(project, snapshot_sha, jobs, WebReporter(self.socketio))

                # update snapshot in project snapshots
                project.initSnapshots()
                webProjects[name]['snapshots'] = [snapshot.to_dict() for snapshot in project.snapshots]

                return { 'success': True, 'snapshot': snapshot.to_dict() }
            except Exception as e:
                return { 'success': False, 'error': str(e) }


        @self.app.route('/api/projects/<name>/snapshot/<snapshot_sha>/reset/<stage>')
        def __resetSnapshot (name, snapshot_sha, stage):
            project = localProjects[name]
            try:
                jobs = [
                    InitRepoAction(),
                    CompileLatexAction(),
                    PdfToImageAction(),
                    AssembleImageAction()
                ]

                if stage is not None and stage.isdigit():
                    jobs = jobs[:int(stage)]

                snapshot = next((s for s in project.snapshots if s.commit_sha == snapshot_sha), None)
                if snapshot is None:
                    raise Exception(f"Snapshot {snapshot_sha} not found")

                # reset all jobs, starting from the last one in case earlier jobs depend on later ones
                for job in reversed(jobs):
                    job.reset(snapshot)
                    snapshot.status[job.getName()] = None
                    saveToFile(f'{snapshot.getWorkDir()}/snapshot.yaml', snapshot)
                
                # reload snapshots from file
                project.initSnapshots()
                webProjects[name]['snapshots'] = [snapshot.to_dict() for snapshot in project.snapshots]
                snapshot = next((s for s in project.snapshots if s.commit_sha == snapshot_sha), None)

                return { 'success': True, 'snapshot': snapshot.to_dict() }
            except Exception as e:
                return { 'success': False, 'error': str(e) }



        @self.app.route('/api/projects/<name>/snapshot/<snapshot>/pdf')
        def getPdf(name, snapshot):
            try:
                project =  localProjects[name]
                snapshot = next((s for s in project.snapshots if s.commit_sha == snapshot), None)
                pdfFile = snapshot.main_tex_file[:-4] + ".pdf"
                filePath = path.join(os.getcwd(), snapshot.getWorkDir(), 'latex', pdfFile)
                return send_file(filePath)
            except Exception as e:
                return str(e)

        @self.app.route('/api/projects/<name>/snapshot/<snapshot>/image/<image>')
        def getImage(name, snapshot, image):
            try:
                project =  localProjects[name]
                snapshot = next((s for s in project.snapshots if s.commit_sha == snapshot), None)
                filePath = path.join(os.getcwd(), snapshot.getWorkDir(), 'images', image)
                return send_file(filePath)
            except Exception as e:
                return str(e)


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
            file_path = os.path.join(UPLOAD_FOLDER, project_file.filename)
            project_file.save(file_path)

            name = init_project(project_name, f'{UPLOAD_FOLDER}/{project_file.filename}')
            self.init_projects(webProjects, localProjects)

            # remove the uploaded file
            os.remove(file_path)

            return jsonify(
                {
                    "message": "Project imported successfully",
                    "name": name
                }
            ), 200

    def send_message(self, message):
        self.socketio.emit('message', message)

    def run(self):
        self.socketio.run(self.app)

    def init_projects(self, webProjects, localProjects):
        for name in list_projects():
            project = Project(name)
            localProjects[name] = project
            webProjects[name] = {
                'name': name,
                'config': project.config,
                'snapshots': [snapshot.to_dict() for snapshot in project.snapshots]
            }

