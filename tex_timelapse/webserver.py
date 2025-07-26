from os import path
import os
from flask import Flask, jsonify, send_file
from flask import request
from flask_socketio import SocketIO # type: ignore
from flask_cors import CORS

from tex_timelapse.reporters.web_reporter import WebReporter
from tex_timelapse.compiler import compileProject, compileSnapshot
from tex_timelapse.project import Project

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
            # project = localProjects[name]
            # try:
            #     rmtree(f'{project.projectFolder}/snapshots', ignore_errors=True)
            #     project.initSnapshots()
            #     webProjects[name]['snapshots'] = [snapshot.to_dict() for snapshot in project.snapshots]
            #     return { 'success': True, 'snapshots': webProjects[name]['snapshots'] }
            # except Exception as e:
                # return { 'success': False, 'error': str(e) }
            return { 'success': False, 'error': 'NYI' }

        @self.app.route('/api/projects/<name>/snapshot/<snapshot_sha>/run')
        def __compileSnapshot(name, snapshot_sha):
            return { 'success': False, 'error': 'NYI' }
            # project = localProjects[name]
            # try:
            #     jobs = [
            #         InitRepoAction(),
            #         CompileLatexAction(),
            #         PdfToImageAction(),
            #         AssembleImageAction()
            #     ]

            #     snapshot = compileSnapshot(project, snapshot_sha, jobs, WebReporter(self.socketio))
            #     matching_snapshot = [s for s in project.snapshots if s.commit_sha == snapshot_sha]

            #     if len(matching_snapshot) == 0:
            #         raise Exception(f"Snapshot {snapshot_sha} not found")
            #     if len(matching_snapshot) > 1:
            #         raise Exception(f"Snapshot {snapshot_sha} found multiple times")

            #     # update snapshot in project snapshots
            #     project.initSnapshots()
            #     webProjects[name]['snapshots'] = [snapshot.to_dict() for snapshot in project.snapshots]

            #     return { 'success': True, 'snapshot': snapshot.to_dict() }
            # except Exception as e:
            #     return { 'success': False, 'error': str(e) }


        @self.app.route('/api/projects/<name>/snapshot/<snapshot_sha>/reset/<stage>')
        def __resetSnapshot (name, snapshot_sha, stage):
            return { 'success': False, 'error': 'NYI' }
            # project = localProjects[name]
            # try:
            #     jobs = [
            #         InitRepoAction(),
            #         CompileLatexAction(),
            #         PdfToImageAction(),
            #         AssembleImageAction()
            #     ]

            #     if stage is not None and stage.isdigit():
            #         jobs = jobs[:int(stage)]

            #     snapshot = next((s for s in project.snapshots if s.commit_sha == snapshot_sha), None)
            #     if snapshot is None:
            #         raise Exception(f"Snapshot {snapshot_sha} not found")

            #     # reset all jobs, starting from the last one in case earlier jobs depend on later ones
            #     snapshot.error = ''
            #     for job in reversed(jobs):
            #         job.reset(snapshot)
            #         snapshot.status[job.getName()] = None
            #         saveToFile(f'{snapshot.getWorkDir()}/snapshot.yaml', snapshot)
                
            #     # reload snapshots from file
            #     project.initSnapshots()
            #     webProjects[name]['snapshots'] = [snapshot.to_dict() for snapshot in project.snapshots]
            #     snapshot = next((s for s in project.snapshots if s.commit_sha == snapshot_sha), None)

            #     return { 'success': True, 'snapshot': snapshot.to_dict() }
            # except Exception as e:
            #     return { 'success': False, 'error': str(e) }



        @self.app.route('/api/projects/<name>/snapshot/<snapshot>/pdf')
        def getPdf(name, snapshot):
            return { 'success': False, 'error': 'NYI' }
            # try:
            #     project =  localProjects[name]
            #     snapshot = next((s for s in project.snapshots if s.commit_sha == snapshot), None)
            #     pdfFile = snapshot.main_tex_file[:-4] + ".pdf"
            #     filePath = path.join(os.getcwd(), snapshot.getWorkDir(), 'latex', pdfFile)
            #     return send_file(filePath)
            # except Exception as e:
            #     return str(e)

        @self.app.route('/api/projects/<name>/snapshot/<snapshot>/image/<image>')
        def getImage(name, snapshot, image):
            return { 'success': False, 'error': 'NYI' }
            # try:
            #     project =  localProjects[name]
            #     snapshot = next((s for s in project.snapshots if s.commit_sha == snapshot), None)
            #     filePath = path.join(os.getcwd(), snapshot.getWorkDir(), 'images', image)
            #     return send_file(filePath)
            # except Exception as e:
            #     return str(e)


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

            project = Project.create(project_name, f'{UPLOAD_FOLDER}/{project_file.filename}')

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
