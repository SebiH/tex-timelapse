#!/usr/bin/env python3

from multiprocessing.pool import ThreadPool
import re
from shutil import rmtree
import git
import subprocess
import os
from PIL import Image, ImageFilter, ImageDraw
from distutils.dir_util import copy_tree, remove_tree
from glob import glob
import numpy as np
from alive_progress import alive_bar
import argparse
from ffmpeg_progress_yield import FfmpegProgress


############################
# Argument parsing
############################
parser = argparse.ArgumentParser(description='Visualize the creation of a LaTeX document as timelapse.')
parser.add_argument('pathToTexFile', type=str,
                    help='Path to main tex file (should include .git folder!)', default='source/main.tex')

parser.add_argument('--output', type=str,
                    help='Output video filename.', default='output.mp4')

parser.add_argument('--blur', type=float,
                    help='Amount of gaussian blur.', default=1)

parser.add_argument('--rows', type=int,
                    help='Number of rows in final video.', default=3)

parser.add_argument('--columns', type=int,
                    help='Number of columns in final video.', default=6)

parser.add_argument('--highlight-changes', dest='highlightChanges',
                    type=bool, default=True,
                    help='Highlight changes based on git commits and synctex (default true)')
parser.add_argument('--fade-effect', dest='fadeEffect',
                    type=bool, default=False,
                    help='Slowly fades out the changes from previous commits (requires --highlight-changes)')


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
diffFile = '__diff__.txt'
pagesFile = '__changed_pages__.txt'

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

    if args.highlightChanges:
        highlightCmd = f'git diff --unified=0 HEAD HEAD~1 {texFile}'
        with open(os.path.join(workDir, diffFile), 'w') as f:
            process = subprocess.Popen(highlightCmd.split(), stdout=f, stderr=stdout, cwd=workDir)
            process.wait()

    rmtree(f'{workDir}/.git')


def compilePdf(commit):
    cmd = f'latexmk -pdf {"--synctex=1" if args.highlightChanges else ""} -interaction=nonstopmode {texFile}'
    workDir = getWorkDir(commit)
    process = subprocess.Popen(cmd.split(), stdout=stdout, stderr=stdout, cwd=workDir)
    process.wait()

    if args.highlightChanges:
        try:
            # find \begin{document} and \end{document} to only highlight changes within document, not preamble etc
            with open(os.path.join(workDir, texFile), 'r') as f:
                content = f.readlines()
                documentSpan = [0, len(content)]
                i = 0
                for line in content:
                    i += 1
                    if '\\begin{document}' in line:
                        documentSpan[0] = i
                    if '\\end{document}' in line:
                        documentSpan[1] = i

            # transform changed lines into pages using synctex
            with open(os.path.join(workDir, diffFile), 'r') as f:
                content = f.read()
                changedLines = set()

                # git format example: @@ -33,5 55,4 @@
                #                         ^  ^ ^  ^
                #                         |  | |  |
                #              Removed Line  | Added line
                #                            |    |
                #                      Number of removed / added lines (may be optional)
                #
                # The following code extracts these values and puts both removed and added lines into the changedLines array
                for match in re.finditer(r'@@\s+-(\d+),?(\d*)\s+\+(\d+),?(\d*)\s+@@', content):
                    for x in range(int(match.group(1)), int(match.group(1)) + int(match.group(2) if match.group(2) else 0) + 1):
                        changedLines.add(x)
                    for x in range(int(match.group(3)), int(match.group(3)) + int(match.group(4) if match.group(4) else 0) + 1):
                        changedLines.add(x)

                changedLines = [line for line in changedLines if documentSpan[0] < line and line < documentSpan[1]]

            changedPages = set()
            for line in changedLines:
                synctexCmd = f'synctex view -i {line}:0:{os.path.abspath(workDir)}/./{texFile} -o {pdfFile}'
                process = subprocess.Popen(synctexCmd.split(), stdout=subprocess.PIPE, stderr=stdout, cwd=workDir)
                out, err = process.communicate()
                out = str(out)

                try:
                    page = int(re.search(r"Page:(\d*)", out, flags=re.MULTILINE).group(1))
                    changedPages.add(page)
                except:
                    print(workDir)
                    print(synctexCmd)
                    pass

                # TODO: interpret this output correctly other than the page?
                # x = float(re.search(r"x:(\d*\.?\d*)", out, flags=re.MULTILINE).group(1))
                # y = float(re.search(r"y:(\d*\.?\d*)", out, flags=re.MULTILINE).group(1))
                # h = float(re.search(r"h:(\d*\.?\d*)", out, flags=re.MULTILINE).group(1))
                # v = float(re.search(r"v:(\d*\.?\d*)", out, flags=re.MULTILINE).group(1))
                # W = float(re.search(r"W:(\d*\.?\d*)", out, flags=re.MULTILINE).group(1))
                # H = float(re.search(r"H:(\d*\.?\d*)", out, flags=re.MULTILINE).group(1))

            # write pages back to file for later processing
            with open(os.path.join(workDir, pagesFile), 'w') as f:
                for p in changedPages:
                    f.write(str(p) + '\n')
        except:
            print('Error')
            print(workDir)
            pass


def pdfToImage(commit):
    try:
        workDir = getWorkDir(commit)
        cmd = f'pdftoppm -png {workDir}/{pdfFile} {workDir}/__visualizer__'
        process = subprocess.Popen(cmd.split(), stdout=stdout, stderr=stdout)
        process.wait()
    except Exception as e:
        print(e)


# TODO: breaks in multithreading mode!
changedPageTracker = {}

def compileImages(commit: git.Commit):
    try:
        workDir = getWorkDir(commit)

        images = [Image.open(x).filter(ImageFilter.GaussianBlur(args.blur)) for x in glob(f'{workDir}/__visualizer__*.png')]
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

        fadeRepetitions = 1
        if args.fadeEffect:
            fadeRepetitions = 5
            with open(os.path.join(workDir, pagesFile), 'r') as f:
                for line in f.readlines():
                    if line:
                        changedPageTracker[line] = 1
                        
        for fadeRepetition in range(fadeRepetitions):
            # clone images to apply fade effect without stacking overlays
            hlImages = []
            for i in images:
                hlImages.append(i)

            if args.highlightChanges:
                if not args.fadeEffect:
                    overlay = Image.new('RGBA', images[0].size, '#A3BE8C66')
                    with open(os.path.join(workDir, pagesFile), 'r') as f:
                        for line in f.readlines():
                            if line and int(line) <= len(images):
                                line = int(line)
                                img = images[line-1].convert('RGBA')
                                img = Image.alpha_composite(img, overlay)
                                hlImages[line-1] = img

                if args.fadeEffect:
                    with open(os.path.join(workDir, pagesFile), 'r') as f:
                        # fade effect
                        for key in list(changedPageTracker):
                            changedPageTracker[key] -= 0.05
                            if changedPageTracker[key] < 0.01:
                                changedPageTracker.pop(key)

                        for line in changedPageTracker:
                            overlay = Image.new('RGBA', images[0].size, f'#A3BE8C{int(changedPageTracker[line]*102):0>2X}')
                            line = int(line)
                            img = images[line-1].convert('RGBA')
                            img = Image.alpha_composite(img, overlay)
                            hlImages[line-1] = img

            img = pil_grid(hlImages, args.columns)
            img.save(f'output/commit_{commit.authored_date}_{fadeRepetition:02}.png')
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
            for job in reversed(jobs):
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
        os.replace(file, os.path.join('output', f'{i:05d}.png'))
        i += 1

else:
    print('Skipping')

pool.close()
pool.join()


print('Rendering video')
if should['renderVideo']:
    framerate = 5
    if args.fadeEffect:
        framerate *= 5
    cmd = f'ffmpeg -y -framerate {framerate} -start_number 0 -i output/%05d.png -c:v libx264 -movflags +faststart -vf format=yuv420p,scale=iw*0.25:ih*0.25,pad=ceil(iw/2)*2:ceil(ih/2)*2:0:0:white -strict -2 output/{args.output}'
    ff = FfmpegProgress(cmd.split(' '))
    with alive_bar(total=100) as bar:
        for progress in ff.run_command_with_progress():
            bar(progress - bar.current())
else:
    print('Skipping')
