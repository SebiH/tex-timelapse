#!/usr/bin/env python3

import argparse

from tex_timelapse.reporters.terminal_reporter import TerminalReporter
from tex_timelapse.compiler import compileProject
from tex_timelapse.project import Project
from tex_timelapse.snapshot import SnapshotStatus
from tex_timelapse.webserver import WebServer


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

initParser.add_argument(
    'source',
    type=str,
    help='Source folder containing the .git repository of the LaTeX project')

# -----------
# --- run ---
# -----------
runParser = subparsers.add_parser(
    'run', help='Run a project')

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


def runProject(name: str, output: str, args):
    print(f"Running project '{name}'...")
    project = Project.deserialize(name)
    project.loadSnapshots()

    from tex_timelapse.actions.init_repo import InitRepoAction
    from tex_timelapse.actions.compile_latex import CompileLatexAction
    from tex_timelapse.actions.pdf_to_image import PdfToImageAction
    from tex_timelapse.actions.assemble_image import AssembleImageAction
    jobs = [
        InitRepoAction(),
        CompileLatexAction(),
        PdfToImageAction(),
        AssembleImageAction()
    ]

    if args.stage is not None:
        foundStage = False

        for job in jobs:
            jobName = job.getName()
            foundStage = jobName == args.stage
            if foundStage:
                for snapshot in project.snapshots:
                    snapshot.status[jobName] = SnapshotStatus.PENDING

    compileProject(project, output, jobs, TerminalReporter())


def listProjects():
    print("Available projects:")
    for project in Project.list():
        print(f" - {project.name} ({len(project.snapshots)} snapshots)")


############################
# Main
############################

args = parser.parse_args()

if (args.action == 'init'):
    Project.create(args.project, args.source)
elif (args.action == 'run'):
    runProject(args.project, args.output, args)
elif (args.action == 'list'):
    listProjects()
elif (args.action == 'server'):
    WebServer().run()
    
else:
    print(f"Unknown action '{args.action}'")
    parser.print_help()
