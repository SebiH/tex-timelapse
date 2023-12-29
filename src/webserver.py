from flask import Flask
from flask import request
from .project import list_projects, load_project

class WebServer:
    def create_server(test_config=None):
        app = Flask(__name__)

        projects = list_projects()

        @app.route('/projects')
        def listProjects():
            return list_projects()

        @app.route('/projects/<name>')
        def project(name):
            project = load_project(name)
            print([snapshot.__dict__ for snapshot in project.snapshots[0:2]])
            return { 
                'config': project.config,
                'snapshots': [snapshot.to_json() for snapshot in project.snapshots]
            }

        @app.route('/projects/<name>/run', methods=['POST'])
        def runProject():
            print(request.form)
            return list_projects()

        return app