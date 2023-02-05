# TeX Timelapse

Visualizes the (git) history of a LaTeX project as a timelapse video. Requires the full history of a latex project (see also "Not supported (yet)" section).

[example.webm](https://user-images.githubusercontent.com/2853456/212557287-f717ed4b-2a64-4d33-afd4-96a2513947f1.webm)


## Usage
### Docker (Linux/MacOS):
```bash
docker run -it -v ${CWD}/YOUR_SOURCE:/visualizer/source -v ${CWD}/tmp:/visualizer/tmp -v ${CWD}/output:/visualizer/output sebih/tex-history-visualizer source/YOUR_MAIN.tex
```

### Docker (Windows):
*Note: you may want to copy the files to WSL anyway and use the Linux command due to performance issues when reading/writing files from outside of WSL*
```bash
docker run -it -v ${PWD}/YOUR_SOURCE:/visualizer/source -v ${PWD}/tmp:/visualizer/tmp -v ${PWD}/output:/visualizer/output sebih/tex-history-visualizer source/YOUR_MAIN.tex
```

### Raw (Python)
- Install: `pip install -r requirements.txt`
- Run: `py generate.py PATH/TO/MAIN.tex`

## Parameters
  - `-h, --help`: show help message and exit
  - `--output <OUTPUT: string>`: Output video filename (default: output.mp4).
  - `--blur <BLUR: number>`: Amount of gaussian blur (default: 1).
  - `--rows <ROWS: number>`: Number of rows in final video (default: 3).
  - `--columns <COLUMNS: number>`: Number of columns in final video (default: 6).
  - `--highlight-changes <HIGHLIGHTCHANGES: true|false>` Highlight changes based on git commits and synctex (default true).
  - `--fade-effect <FADEEFFECT: true|false>`: Slowly fades out the changes from previous commits (requires --highlight-changes, default: false)
  - ~~`--use-multithreading`: Use multithreading (use with caution - may lead to bugs).~~ Does not work (yet)
  - ~~`--workers <WORKERS: number>`: Number of worker threads (requires multithreading).~~ Does not work (yet)
  - `--test-run`: Performs a quick test run with 10 commits and prints output to console. Useful for debugging.
  - `--skip-step <SKIP: number>`: Skips specified worksteps. Useful for faster re-rendering (e.g. by skipping directly to rendering step).
    - 1: Initialize repositories in `tmp/` folder
    - 2: Compile PDF and write changes from git/synctex to file
    - 3: Convert PDF pages to images
    - 4: Compile images into one big file; add change highlight
    - 5: Render video

## Not supported (yet)
- Multithreading
- Splitting source files into multiple tex files
- Exporting history from Overleaf as individual git commits
- Visualize datetime (e.g., timeslider, git tags)
