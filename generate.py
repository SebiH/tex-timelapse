#!/usr/bin/env python3

from multiprocessing.pool import ThreadPool
from shutil import rmtree
import git
import subprocess
import os
from PIL import Image, ImageFilter
from distutils.dir_util import copy_tree, remove_tree
from glob import glob
import numpy as np
from alive_progress import alive_bar
import argparse


############################
# Argument parsing
############################
parser = argparse.ArgumentParser(description='Visualize the creation of a LaTeX document.')
parser.add_argument('pathToTexFile', type=str,
                    help='Path to main tex file (should include .git folder!)', default='source/main.tex')

parser.add_argument('--output', type=str,
                    help='Output video filename.', default='output.mp4')

parser.add_argument('--rows', type=int,
                    help='Number of rows in final video.', default=3)

parser.add_argument('--columns', type=int,
                    help='Number of columns in final video.', default=6)

parser.add_argument('--use-multithreading', dest='useMultithreading',
                    help='Use multithreading (use with caution - may lead to bugs).',
                    action='store_true')
parser.add_argument('--workers', type=int,
                    help='Number of worker threads (requires multithreading).', default=16)

parser.add_argument('--test-run', dest='testrun', action='store_true',
                    help='Performs a quick test run with 10 commits and prints output to console. Useful for debugging.')

parser.add_argument('--skip-step', dest='skip', type=int, default=0,
                    help='Skips specified worksteps.')

args = parser.parse_args()


############################
# Constants
############################
workDir = './tmp'

texFile = os.path.basename(args.pathToTexFile)
texFolder = os.path.dirname(args.pathToTexFile)

# check if script is inside source folder -- since we're copying the folder for each
# commit, we don't want to copy the workDir recursively
if not texFolder or os.path.abspath(texFolder) in os.path.dirname(os.path.realpath(__file__)):
    print('Script must be located outside of source folder!')
    exit()

# worksteps
should = {
    'initRepo': args.skip <= 0,
    'compilePdf': args.skip <= 1,
    'pdfToImage': args.skip <= 2,
    'compileImages': args.skip <= 3,
    'renderVideo': args.skip <= 4
}


############################
# Code
############################
if args.testrun:
    stdout = subprocess.PIPE
else:
    stdout = subprocess.DEVNULL

pdfFile = texFile.replace('.tex', '.pdf')

# see https://stackoverflow.com/a/46877433/4090817
def pil_grid(images, max_horiz=np.iinfo(int).max):
    n_images = len(images)
    n_horiz = min(n_images, max_horiz)
    h_sizes, v_sizes = [0] * n_horiz, [0] * ((n_images // n_horiz) + (1 if n_images % n_horiz > 0 else 0))
    for i, im in enumerate(images):
        h, v = i % n_horiz, i // n_horiz
        h_sizes[h] = max(h_sizes[h], im.size[0])
        v_sizes[v] = max(v_sizes[v], im.size[1])
    h_sizes, v_sizes = np.cumsum([0] + h_sizes), np.cumsum([0] + v_sizes)
    im_grid = Image.new('RGB', (h_sizes[-1], v_sizes[-1]), color='white')
    for i, im in enumerate(images):
        im_grid.paste(im, (h_sizes[i % n_horiz], v_sizes[i // n_horiz]))
    return im_grid

def getWorkDir(commit):
    return os.path.join(workDir, commit.hexsha)

def initRepo(commit):
    workDir = getWorkDir(commit)
    copy_tree(f'./{texFolder}/.git', f'{workDir}/.git')
    cmd = f'git reset --hard {commit.hexsha}'
    process = subprocess.Popen(cmd.split(), stdout=stdout, stderr=stdout, cwd=workDir)
    process.wait()
    rmtree(f'{workDir}/.git')


def compilePdf(commit):
    cmd = f'latexmk -pdf -interaction=nonstopmode {texFile}'
    process = subprocess.Popen(cmd.split(), stdout=stdout, stderr=stdout, cwd=getWorkDir(commit))
    process.wait()


def pdfToImage(commit):
    try:
        workDir = getWorkDir(commit)
        cmd = f'./pdftopng.exe {workDir}/{pdfFile} {workDir}/__visualizer__'
        process = subprocess.Popen(cmd.split(), stdout=stdout, stderr=stdout)
        process.wait()
    except Exception as e:
        print(e)

def compileImages(commit: git.Commit):
    try:
        workDir = getWorkDir(commit)
        images = [Image.open(x).filter(ImageFilter.BLUR) for x in glob(f'{workDir}/__visualizer__*.png')]
        if (len(images) == 0):
            raise Exception(f'No images found for {commit.hexsha}')

        while (len(images) < args.rows * args.columns):
            images.append(Image.new('RGB', (1275, 1651), color='white'))
        while ((len(images)) >= args.rows * args.columns):
            images.pop()

        for i in range(len(images)):
            if i % 2 != 0:
                images[i] = images[i].crop((200, 130, 1150, 1380))
            else:
                images[i] = images[i].crop((130, 130, 1080, 1380))

        img = pil_grid(images, args.columns)
        img.save(f'output/commit_{commit.authored_date}.png')
    except Exception as e:
        print(e)

def execute(function, jobs):
    with alive_bar(len(jobs)) as bar:
        if args.useMultithreading:
            pool.map(lambda commit: (
                function(commit),
                bar()
            ), jobs)
        else:
            for job in jobs:
                bar.text = job.hexsha
                function(job)
                bar()


pool = ThreadPool(args.workers)
repo = git.Repo(texFolder)
if args.testrun:
    jobs = list(repo.iter_commits(max_count=10))
else:
    jobs = list(repo.iter_commits())

print('Initializing repositories')
if should['initRepo']:
    execute(initRepo, jobs)
else:
    print('Skipping')

print('Compiling PDF')
if should['compilePdf']:
    execute(compilePdf, jobs)
else:
    print('Skipping')

print('Converting PDF to image')
if should['pdfToImage']:
    execute(pdfToImage, jobs)
else:
    print('Skipping')

print('Compiling images')
if should['compileImages']:
    execute(compileImages, jobs)
    i = 0
    for file in sorted(glob('output/commit_*.png')):
        os.replace(file, os.path.join('output', f'{i:04d}.png'))
        i += 1

else:
    print('Skipping')

pool.close()
pool.join()


print('Rendering video')
if should['renderVideo']:
    cmd = f'ffmpeg -y -framerate 5 -start_number 0 -i %04d.png -c:v libx264 -vf format=yuv420p,scale=iw*0.25:ih*0.25,pad=ceil(iw/2)*2:ceil(ih/2)*2 ../{args.output}'
    process = subprocess.Popen(cmd.split(), stdout=stdout, stderr=stdout, cwd='./output')
    process.wait()
else:
    print('Skipping')
