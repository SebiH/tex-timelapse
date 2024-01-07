#!/usr/bin/env python3

import argparse
import os
import shutil

from slugify import slugify

from src.runners.terminal_runner import TerminalReporter
from src.compiler import compileProject
from src.project import Project, list_projects
from src.webserver import WebServer


############################
# Argument parsing
############################

parser = argparse.ArgumentParser(description='Visualize the creation of a LaTeX document as timelapse.')

subparsers = parser.add_subparsers(dest='action')
subparsers.required = True

# ------------
# --- init ---
# ------------
initParser = subparsers.add_parser(
    'init', help='Initialize a new project')
initParser.add_argument(
    'project',
    type=str,
    help='Name of the project')

# -----------
# --- run ---
# -----------
runParser = subparsers.add_parser(
    'run', help='Run a project')
# add a required argument
runParser.add_argument(
    'project',
    type=str,
    help='Name of the project')

runParser.add_argument(
    'output',
    type=str,
    help='Output')

runParser.add_argument(
    '--stage',
    type=int,
    help='Start from stage (default: all)')

# TODO: non-project-specific general arguments; add these to docker-compose.yml
# workers: int # TODO: -1 should set to cpu count; 1 should disable multiprocessing

# ------------
# --- list ---
# ------------
listParser = subparsers.add_parser('list', help='List all projects')

# --------------
# --- server ---
# --------------
serverParser = subparsers.add_parser('server', help='Server')


############################
# Actions
############################

def initProject(name: str):
    print(f"Initializing project '{name}' with default values...")
    
    # create folder
    folder = f'./projects/{slugify(name)}'
    os.makedirs(folder, exist_ok=True)

    # copy default config
    shutil.copyfile('./default_config.yaml', f'{folder}/project.yaml')

    # output
    print(f"Project '{name}' successfully initialized in '{folder}'. Please edit the project.yaml file, then run:")
    print(f"run...")


def runProject(name: str, output: str, args):
    print(f"Running project '{name}'...")
    project = Project(name)

    if args.stage is not None:
        project.setStage(args.stage)

    from src.jobs.init_repo import InitRepoJob
    from src.jobs.compile_latex import CompileLatexJob
    from src.jobs.pdf_to_image import PdfToImageJob
    from src.jobs.assemble_image import AssembleImageJob
    jobs = [
        InitRepoJob(),
        CompileLatexJob(),
        PdfToImageJob(),
        AssembleImageJob()
    ]

    compileProject(project, output, jobs, TerminalReporter())


def listProjects():
    print("Available projects:")
    for project in list_projects():
        print(f" - {project}");


############################
# Main
############################

args = parser.parse_args()

if (args.action == 'init'):
    initProject(args.project)
elif (args.action == 'run'):
    runProject(args.project, args.output, args)
elif (args.action == 'list'):
    listProjects()
elif (args.action == 'server'):
    WebServer.create_server().run()
    
else:
    print(f"Unknown action '{args.action}'")
    parser.print_help()
