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
Install the OS dependencies:

  - a TeX distribution (TeX Live or MiKTeX)
  - `latexmk`
  - `texliveonfly` - either via package manager (e.g. `apt install texlive-extra-utils`) or via the TeX Live manager (`tlmgr install texliveonfly`)
  - `git`
  - `ffmpeg`
  - `python3`

PDF rasterisation needs no system package - it goes through the `pypdfium2`
wheel, which bundles PDFium. (`poppler-utils`/`pdftoppm` is no longer required.)

Then install the python dependencies and run a project:

```bash
pip install -r requirements.txt
python tex-timelapse.py init myproject path/to/myproject.zip
python tex-timelapse.py run myproject timelapse
```

Run from the repository root: `./projects` and `./default_config.yaml` are
resolved relative to the current working directory.


## CLI

```
python tex-timelapse.py init <project> <source.zip>
python tex-timelapse.py run <project> <output> [--stage <name>]
python tex-timelapse.py list
python tex-timelapse.py server [--host HOST] [--port PORT]
```

  - **`init`** creates `projects/<slugified-name>/` and unpacks `<source.zip>`
    into it. Only `.zip` sources are supported, and the archive must contain
    the project's `.git` directory - the git history *is* the timelapse.
  - **`run`** compiles the project and writes `projects/<name>/output/<output>.mp4`.
    `<output>` is a basename, not a path.
  - **`--stage <name>`** resets the named pipeline stage and every stage after
    it, then recomputes only those - useful for re-rendering without
    recompiling. Accepts a stage name, case-insensitively: `Init Repository`,
    `Replace Text`, `Compile LaTeX`, `PDF to Image`, `Assemble Image`.
  - **`server`** starts the Flask + Socket.IO API. It binds to loopback only by
    default; pass `--host 0.0.0.0` to accept connections from other machines
    (required inside a container).

Progress is resumable: per-commit state lives in `projects/<name>/snapshots.yaml`,
so an interrupted run picks up where it stopped instead of recompiling
everything. Delete that file (or use the web UI's reset) to start over.


## Configuration

Each project gets a `project.yaml`, copied from `default_config.yaml` at init
time and editable afterwards either by hand or through the web UI. The keys:

| Key | Default | Meaning |
|---|---|---|
| `rows`, `columns` | `3`, `6` | Grid the PDF pages are tiled into for each frame. Pages beyond `rows × columns` are dropped; a short document is padded with blank pages. |
| `framerate` | `8` | Output video framerate. |
| `videoscale` | `0.25` | Scale factor applied by ffmpeg to the assembled frames. |
| `blur` | `1` | Gaussian blur radius applied to each page. The point is to make the text unreadable so the *shape* of the document reads as the subject. `0` disables it. |
| `highlightChanges` | `true` | Highlight regions changed by each commit, located by mapping `git diff` line numbers to PDF coordinates via synctex. |
| `startCommit`, `endCommit` | `''` | Restrict the timelapse to a commit range instead of the full history. |
| `startDate`, `endDate` | empty | Same, by date. |
| `crop*` | `false` / `0` | Per-page cropping, including alternating left/right offsets for two-page layouts. |
| `latexCmd` | `latexmk -pdf -interaction=nonstopmode -synctex=1 -f` | The compile command. `latexmk` is the default because it handles reruns and the bibliography pass itself; a custom non-latexmk command gets a **single** pass only. |
| `concatCommits` | `0` | Collapse N commits into one snapshot (one video frame). `0` means no concatenation - one frame per commit. |
| `workers` | `-1` | Worker threads. `-1` uses the default pool size, `1` disables concurrency, `N` uses exactly N. |
| `text_replacements` | `³`→`3`, `⁈`→`?!` | Literal substitutions applied to the sources before compiling; a workaround for characters that break the compiler. |
| `overleafProjectId`, `overleafAuthToken` | `''` | Reserved for Overleaf import; not yet implemented. |

A compile is judged successful by whether a PDF appeared, not by the compiler's
exit code - LaTeX routinely exits non-zero on documents that render fine.


## Web UI

The web UI (`webui/`, Vite + React) is a separate front end over the same
pipeline. Under Docker it is built and served for you (see above). For
development, run the API and the Vite dev server side by side:

```bash
python tex-timelapse.py server      # :5000
cd webui && npm install && npm run dev   # :5173, proxies /api and /socket.io
```

Node 18+ is required. The Flask server does **not** serve the built UI - in
production that is nginx's job, as configured in `docker/nginx.conf`.


## Not supported (yet)
- Exporting history from Overleaf as individual git commits
- Visualize datetime (e.g., timeslider, git tags)
