from os import path
import os
from flask import Flask, send_file
from flask import request

from .snapshot import Snapshot
from .project import TimelapseProject, list_projects, load_project

class WebServer:
    def create_server(test_config=None):
        app = Flask(__name__)

        webProjects = {}
        localProjects: dict[str, TimelapseProject] = {}
        
        for name in list_projects():
            project = load_project(name)
            localProjects[name] = project
            webProjects[name] = {
                'config': project.config,
                'snapshots': [snapshot.to_json() for snapshot in project.snapshots]
            }

        @app.route('/api/projects')
        def listProjects():
            return list(webProjects.keys())

        @app.route('/api/projects/<name>')
        def getProject(name):
            return webProjects[name]

        @app.route('/api/projects/<name>', methods=['PUT'])
        def createProject(name):
            return True

        @app.route('/api/projects/<name>', methods=['POST'])
        def editProject(name):
            return True

        @app.route('/api/projects/<name>/run')
        def runProject(name):
            print(request.form)
            return list_projects()

        @app.route('/api/projects/<name>/snapshot/<snapshot>/run')
        def compileSnapshot(name, snapshot):
            print(request.form)
            return list_projects()

        @app.route('/api/projects/<name>/snapshot/<snapshot>/pdf')
        def getPdf(name, snapshot):
            try:
                project =  localProjects[name]
                snapshot = next((s for s in project.snapshots if s.commit_sha == snapshot), None)
                pdfFile = snapshot.main_tex_file[:-4] + ".pdf"
                filePath = path.join(os.getcwd(), snapshot.getWorkDir(), 'latex', pdfFile)
                return send_file(filePath)
            except Exception as e:
                return str(e)

        @app.route('/api/projects/<name>/snapshot/<snapshot>/image/<image>')
        def getImage(name, snapshot, image):
            try:
                project =  localProjects[name]
                snapshot = next((s for s in project.snapshots if s.commit_sha == snapshot), None)
                filePath = path.join(os.getcwd(), snapshot.getWorkDir(), 'images', image)
                return send_file(filePath)
            except Exception as e:
                return str(e)
        

        return app