#!/usr/bin/env python3

import argparse
import os
import shutil
from glob import glob
from slugify import slugify
from src.project import TimelapseProject
from src.projectconfig import ProjectConfig
from src.util.serialization import loadFromFile


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

# ------------
# --- list ---
# ------------
listParser = subparsers.add_parser('list', help='List all projects')

args = parser.parse_args()

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

    projectName = slugify(name)
    # load project from file
    config: ProjectConfig = loadFromFile(f'./projects/{projectName}/project.yaml')
    project = TimelapseProject(projectName, config)
    
    if args.stage is not None:
        project.setStage(args.stage)

    project.run(output)


def listProjects():
    print("Available projects:")
    for file in glob(f'projects/**/project.yaml', recursive=True):
        print(f" - {os.path.dirname(file).removeprefix('projects/')}");


############################
# Main
############################

if (args.action == 'init'):
    initProject(args.project)
elif (args.action == 'run'):
    runProject(args.project, args.output, args)
elif (args.action == 'list'):
    listProjects()
else:
    print(f"Unknown action '{args.action}'")
    parser.print_help()
