#!/bin/py

from multiprocessing.pool import ThreadPool
from shutil import rmtree
import git
import subprocess
import os
from PIL import Image
from distutils.dir_util import copy_tree, remove_tree
from glob import glob
import numpy as np
from multiprocessing import Pool
from alive_progress import alive_bar

############################
# Constants
############################
workDir = './tmp'
outputFile = 'out.mp4'

maxColumns = 8
maxRows = 3

texFile = 'paper.tex'
texFolder = 'overleaf'

useMultithreading = True
maxWorkers = 16

debugMode = False

# worksteps
should = {
    'initRepo': True,
    'compilePdf': True,
    'pdfToImage': True,
    'compileImages': True,
    'renderVideo': True
}


############################
# Code
############################
if debugMode:
    stdout = subprocess.PIPE
else:
    stdout = subprocess.DEVNULL

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
        cmd = f'wsl pdftoppm paper.pdf -png __visualizer__'
        process = subprocess.Popen(cmd.split(), stdout=stdout, stderr=stdout, cwd=getWorkDir(commit))
        process.wait()
    except Exception as e:
        print(e)

def compileImages(commit):
    try:
        workDir = getWorkDir(commit)
        images = [Image.open(x) for x in glob(f'{workDir}/__visualizer__*.png')]
        while (len(images) < maxRows * maxColumns):
            images.append(Image.new('RGB', (1275, 1651), color='white'))
        while ((len(images)) >= maxRows * maxColumns):
            images.pop()

        img = pil_grid(images, maxColumns)
        img.save(f'output/commit_{commit.committed_date}.png')
    except Exception as e:
        print(e)

def execute(function, jobs):
    with alive_bar(len(jobs)) as bar:
        if useMultithreading:
            pool.map(lambda commit: (
                function(commit),
                bar()
            ), jobs)
        else:
            for job in jobs:
                function(job)
                bar()


pool = ThreadPool(maxWorkers)
repo = git.Repo(texFolder)
if debugMode:
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
else:
    print('Skipping')

pool.close()
pool.join()

i = 0
for file in sorted(glob('output/commit_*.png')):
    os.replace(file, os.path.join('output', f'{i}.png'))
    i += 1


print('Rendering video')
if should['renderVideo']:
    cmd = f'ffmpeg -y -framerate 5 -start_number 0 -i %d.png -c:v libx264 -vf format=yuv420p,scale=iw*0.25:ih*0.25,pad=ceil(iw/2)*2:ceil(ih/2)*2 {outputFile}'
    process = subprocess.Popen(cmd.split(), stdout=stdout, stderr=stdout, cwd='./output')
    stdout, stderr = process.communicate()
else:
    print('Skipping')
