from os import path
import os
from flask import Flask, send_file
from flask import request
from flask_socketio import SocketIO
from flask_cors import CORS

from tex_timelapse.reporters.web_reporter import WebReporter
from tex_timelapse.compiler import compileSnapshot
from tex_timelapse.project import Project, list_projects

class WebServer:
    def __init__(self):
        self.app = Flask(__name__)

        CORS(self.app, resources={r"/*": {"origins": "*"}})
        self.socketio = SocketIO(self.app, cors_allowed_origins='*')

        webProjects = {}
        localProjects: dict[str, Project] = {}
        
        for name in list_projects():
            project = Project(name)
            localProjects[name] = project
            webProjects[name] = {
                'name': name,
                'config': project.config,
                'snapshots': [snapshot.to_dict() for snapshot in project.snapshots]
            }

        @self.app.route('/api/projects')
        def listProjects():
            return list(webProjects.keys())

        @self.app.route('/api/projects/<name>')
        def getProject(name):
            return webProjects[name]

        @self.app.route('/api/projects/<name>', methods=['PUT'])
        def createProject(name):
            return True

        @self.app.route('/api/projects/<name>', methods=['POST'])
        def editProject(name):
            return True

        @self.app.route('/api/projects/<name>/run')
        def runProject(name):
            print(request.form)
            return list_projects()

        @self.app.route('/api/projects/<name>/snapshot/<snapshot_sha>/run')
        def __compileSnapshot(name, snapshot_sha):
            project = localProjects[name]
            try:
                from .actions.init_repo import InitRepoAction
                from .actions.compile_latex import CompileLatexAction
                from .actions.pdf_to_image import PdfToImageAction
                from .actions.assemble_image import AssembleImageAction
                jobs = [
                    InitRepoAction(),
                    CompileLatexAction(),
                    PdfToImageAction(),
                    AssembleImageAction()
                ]

                snapshot = compileSnapshot(project, snapshot_sha, jobs, WebReporter(self.socketio))
                self.socketio.emit('log', snapshot.to_dict())
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
        
    def send_message(self, message):
        self.socketio.emit('message', message)

    def run(self):
        self.socketio.run(self.app)

