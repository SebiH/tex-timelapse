# TeX Timelapse

Visualizes the (git) history of a LaTeX project as a timelapse video. Requires the full history of a latex project (see also "Not supported (yet)" section).

![example.gif](https://github.com/SebiH/tex-timelapse/blob/master/example.gif)


## Usage
### Docker
Docker is the recommended way to run tex-timelapse: it bundles a TeX Live
install, ffmpeg, and everything else the pipeline shells out to, so you
don't need any of that installed locally.

#### docker compose
`docker-compose.yml` defines two services: `tex-timelapse` (the CLI/Flask
server) and `webui` (the built React UI, served via nginx, which proxies
`/api` and `/socket.io` through to `tex-timelapse` - see
`docker/nginx.conf`). `./projects` and `./uploads` are bind-mounted so
project data and video output land on the host, not just inside the
container.

Run the web server (+ UI) in the background:
```bash
docker compose up -d
# server API on http://localhost:5000, web UI on http://localhost:8080
```

Or use it as a one-off CLI, same subcommands as running `tex-timelapse.py`
directly (`init`, `run`, `list`; see `--help`):
```bash
docker compose run --rm tex-timelapse init myproject source/myproject.zip
docker compose run --rm tex-timelapse run myproject timelapse
docker compose run --rm tex-timelapse list
```

The server binds to loopback only by default, so that running it directly on
a workstation is not silently exposed to the network. Inside a container it
must be started with `server --host 0.0.0.0`, which the compose file already
does.

*Note: on Windows, prefer running from inside WSL rather than a
Windows-side path - bind-mounting from the Windows filesystem into a WSL2
container has a substantial I/O performance penalty.*

#### plain docker
Equivalent to the compose `tex-timelapse` service, without compose:
```bash
docker build --target app -t tex-timelapse .
docker run -it --rm \
  -p 5000:5000 \
  -v "$PWD/projects:/tex-timelapse/projects" \
  -v "$PWD/uploads:/tex-timelapse/uploads" \
  tex-timelapse list
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
