# TeX Timelapse

Visualizes the (git) history of a LaTeX project as a timelapse video. Requires the full history of a latex project (see also "Not supported (yet)" section).

![example.gif](https://github.com/SebiH/tex-timelapse/blob/master/example.gif)


## Usage
### docker-compose
*Note: Edit the docker-compose.yml first to change source path*
```bash
docker-compose run --rm tex-timelapse source/YOUR_MAIN_TEX_FILE.tex <arguments>
```

### docker
*Note: On windows, you may want to copy the files to a 'native' WSL and due to performance bottlenecks when reading/writing files from outside of WSL*
```bash
docker run -it --rm -v ${PWD}/YOUR_SOURCE:/visualizer/source -v ${PWD}/tmp:/visualizer/tmp -v ${PWD}/output:/visualizer/output sebih/tex-timelapse source/YOUR_MAIN.tex
```

### python
- Install OS dependencies:
  - LaTeX
  - texliveonfly - either via package manager (e.g., `apt install texlive-extra-utils`) or texlive manager (`tlmgr install texliveonfly`)
  - latexmk
  - git
  - pdftoppm (e.g., from `poppler-utils`)
  - ffmpeg
  - python3
- Install python dependencies: `pip install -r requirements.txt`
- Run: `python tex-timelapse.py PATH/TO/MAIN.tex`


## Parameters
  - `-h, --help`: show help message and exit
  - `--output <OUTPUT: string>`: Output video filename (default: output.mp4).
  - `--blur <BLUR: number>`: Amount of gaussian blur (default: 1).
  - `--rows <ROWS: number>`: Number of rows in final video (default: 3).
  - `--columns <COLUMNS: number>`: Number of columns in final video (default: 6).
  - `--highlight-changes <HIGHLIGHTCHANGES: true|false>` Highlight changes based on git commits and synctex (default true).
  - `--fade-effect <FADEEFFECT: true|false>`: Slowly fades out the changes from previous commits (requires --highlight-changes, default: false)
  - `--use-multithreading`: Enables multithreading, significantly speeding up processing
  - `--workers <WORKERS: number>`: Number of worker threads (requires multithreading).
  - `--from` / `--to: <COMMIT_SHA>`: Only use defined start/end point for timelapse instead of full git history. (Useful for quickly testing out parameters)
  - `--skip-to <SKIP: number>`: Skips to specified worksteps. Useful for quickly re-rendering (e.g. by skipping directly to rendering step).
    - 1: Initialize repositories in `tmp/` folder
    - 2: Compile PDF and write changes from git/synctex to file
    - 3: Convert PDF pages to images
    - 4: Assemble images into one big file; add change highlight
    - 5: Render video

## Not supported (yet)
- Tracking changes across multiple tex files (e.g., using `\input`)
- Exporting history from Overleaf as individual git commits
- Visualize datetime (e.g., timeslider, git tags)
