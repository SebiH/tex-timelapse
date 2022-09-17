#!/bin/py

import git
import datetime
import subprocess
import os
from PIL import Image
from distutils.dir_util import copy_tree, remove_tree
from glob import glob
import numpy as np

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



repo = git.Repo('overleaf')
i = len(list(repo.iter_commits())) - 1
processes = []
for commit in repo.iter_commits():
    print(f"{commit.committed_datetime.strftime('%Y-%m-%d_%H%M%S')}: {commit.hexsha}")
    workDir = f"./tmp/{commit.hexsha}"
    copy_tree("./overleaf/.git", f"{workDir}/.git")

    initializeRepo = f'git reset --hard {commit.hexsha}'
    compilePdf = f'latexmk -pdf -interaction=nonstopmode paper.tex'
    pdfToImage = f'wsl pdftoppm paper.pdf -png __visualizer__'

    process = subprocess.Popen(initializeRepo.split(), stdout=subprocess.PIPE, cwd=workDir)
    # stdout, stderr = process.communicate()
    processes.append(process)

for p in processes:
    p.wait()
processes = []

for commit in repo.iter_commits():
    workDir = f"./tmp/{commit.hexsha}"
    process = subprocess.Popen(compilePdf.split(), stdout=subprocess.PIPE, cwd=workDir)
    # stdout, stderr = process.communicate()
    processes.append(process)

for p in processes:
    p.wait()
processes = []

for commit in repo.iter_commits():
    workDir = f"./tmp/{commit.hexsha}"
    process = subprocess.Popen(pdfToImage.split(), stdout=subprocess.PIPE, cwd=workDir)
    # stdout, stderr = process.communicate()
    processes.append(process)

    images = [Image.open(x) for x in glob(f'{workDir}/__visualizer__*.png')]
    img = pil_grid(images, 8)
    img.save(f'output/{i}.png')
    i -= 1

# for commit in repo.iter_commits():
    # remove_tree(workDir)

for p in processes:
    p.wait()
processes = []

renderVideo = f'ffmpeg -y -framerate 10 -i %d.png -c:v libx264 -pix_fmt yuv420p -vf pad=ceil(iw/2)*2:ceil(ih/2)*2 out.mp4'
process = subprocess.Popen(renderVideo.split(), stdout=subprocess.PIPE, cwd='./output')
stdout, stderr = process.communicate()
