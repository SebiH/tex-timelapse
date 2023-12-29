from flask import Flask
from flask import request
from .project import list_projects, load_project

class WebServer:
    def create_server(test_config=None):
        app = Flask(__name__)

        projects = {}
        
        for name in list_projects():
            project = load_project(name)
            projects[name] = {
                'config': project.config,
                'snapshots': [snapshot.to_json() for snapshot in project.snapshots]
            }

        @app.route('/api/projects')
        def listProjects():
            return list(projects.keys())

        @app.route('/api/projects/<name>')
        def project(name):
            return projects[name]

        @app.route('/api/projects/<name>/run', methods=['POST'])
        def runProject():
            print(request.form)
            return list_projects()

        return app