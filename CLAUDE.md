# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Turns the git history of a LaTeX project into a timelapse video. Each commit becomes a "snapshot": the repo is reset to that commit, compiled to PDF, rasterized to page images, and tiled into one grid frame. All frames are then encoded with ffmpeg. Changed regions are highlighted by mapping `git diff` line numbers to PDF coordinates via synctex.

Two frontends over the same pipeline: a CLI (`tex-timelapse` console script / repo-root `tex-timelapse.py` shim) and a Flask + Socket.IO server driving a React web UI (`webui/`).

## Layout

The backend is a packaged project under `backend/` (src layout):

```
backend/
  pyproject.toml            deps, [project.scripts] tex-timelapse = tex_timelapse.cli:main
  src/tex_timelapse/
    cli.py                  argparse entry (main())
    paths.py                default_config_path() / projects_root() — no CWD assumptions
    default_config.yaml     shipped as package-data
    core/                   compiler, project, snapshot, config, pdfium_lock, reporter (ABC), actions/  — MUST NOT import flask
    api/                    server (Flask+Socket.IO), jobs
    reporters/              terminal_reporter (no flask), web_reporter / job_reporter (flask)
  tests/                    pytest suite
tex-timelapse.py            repo-root shim: adds backend/src to sys.path, calls cli.main
```

`test_architecture.py` enforces that nothing under `core/` (plus `reporter.py`) imports flask/flask_socketio.

## Commands

Backend (a packaged project; `default_config.yaml` resolves via the package, `projects/` defaults to `$CWD/projects`, override with `TEX_TIMELAPSE_PROJECTS_DIR`):

```bash
pip install -e "./backend[dev]"                    # or: pip install -r requirements.txt (same thing)
tex-timelapse init <name> <source.zip>             # console script; only .zip sources
tex-timelapse run <name> <output>                  # output = mp4 basename
tex-timelapse list
tex-timelapse server                               # Flask on :5000
python tex-timelapse.py <args>                      # repo-root shim, works without install
cd backend && python -m pytest -q                  # backend test suite
mypy backend/src/tex_timelapse --cache-dir=<off-drvfs>   # see the mypy gotcha below
```

Note this checkout's setuptools was too old (59) for PEP 621; `pip install` the backend needs setuptools ≥64 (≥61 to even read `[project]`). Docker's Python 3.11 image is fine.

Web UI (`webui/`, Vite + React 18 + shadcn/ui + Tailwind):

```bash
npm install
npm run dev      # :5173, proxies /api and /socket.io to localhost:5000
npm run build    # tsc && vite build
npm run lint
npm run test     # vitest + React Testing Library
```

The dev server proxy is the only wiring between the two halves — Flask does **not** serve the built web UI, and the Dockerfile does not build it. Running the UI means running `tex-timelapse server` and `npm run dev` side by side.

Tests: `pytest` for the backend (`tests/`, no LaTeX/ffmpeg needed — subprocesses are faked at the `Snapshot.execute_cmd` boundary and pypdfium2 is mocked), `vitest` + RTL for the web UI. An architecture test (`tests/test_architecture.py`) asserts no core pipeline module imports `flask`, guarding a planned `core/` vs `api/` split.

## Architecture

**Project** (`project.py`) — a directory under `projects/<slugified-name>/` holding everything:

```
project.yaml      name + config (copied from default_config.yaml at init)
snapshots.yaml    per-commit state, the pipeline's resume/cache file
source/           unpacked zip, must contain .git
workdir/<tid>/    scratch checkouts, one per worker thread, deleted after a run
thumbnails/<sha>/ 300px page previews for the web UI
frames/           frame_%09d.png, the video's input
output/           <output>.mp4
```

**Snapshot** (`snapshot.py`) — one commit. Carries `commit_sha`, `index` (frame ordering), `status`, per-action `jobs` status, and the data actions pass to each other (`main_tex_file`, `includes`, `gitDiff`, `pages`, `changed_pages`). `execute_cmd()` shells out with `cwd` set to the snapshot's workdir; every action uses it rather than `subprocess` directly.

**Action** (`actions/action.py`) — pipeline stage with `init(project)` / `run(snapshot) -> SnapshotStatus` / `cleanup()` / `reset(snapshot)`. Order matters, each stage consumes the previous stage's fields on the snapshot:

1. `InitRepoAction` — `git reset --hard <sha>`, finds the main `.tex` (first file containing `\begin{document}`), walks `\include`/`\input`/`\addbibresource`/`\includegraphics` to build `includes`, stores `git diff --unified=0` per included file.
2. `ReplaceTextAction` — applies `text_replacements` from config (workaround for characters that break the compiler) and strips `\includeonly`.
3. `CompileLatexAction` — runs `config['latexCmd']` once; the default is `latexmk`, which internally handles reruns and the bibliography pass, while a custom non-latexmk command gets a single pass only. Only if no PDF appears (the symptom of a missing package) does it fall back to `texliveonfly` — probing with the engine derived from `latexCmd` (`_texliveonfly_engine`), not texliveonfly's pdflatex default — and recompile. Success is judged by whether a PDF appeared, not by exit code. Then converts diff line numbers to page coordinates with `synctex view`, writing `changed_pages`.
4. `PdfToImageAction` — renders each page once with `pypdfium2` at 150/72 scale (matching `pdftoppm`'s old 150 DPI output), saving full-size pages (`pages`) plus a Pillow-downscaled 300px thumbnail. Filenames keep `pdftoppm`'s zero-padding (`page-01.jpg`) because several plain lexicographic sorts depend on it.
5. `AssembleImageAction` — scales/blurs pages, draws the change overlays, tiles into `rows × columns`, writes `frames/frame_<index>.png`.

**compiler.py** — `compileProject` fans snapshots out over a module-level `ThreadPoolExecutor` (sized from the `workers` config via `setThreads()`; `-1` means the default pool, `1` disables concurrency), then runs ffmpeg over `frames/*.png`. After the compile loop it aborts (raises) if any snapshot ended `FAILED`, unless `allowPartialRender` is set — a failed compile does **not** raise out of `compileSnapshot` (it returns a `FAILED`-status snapshot), so without this check the run would silently encode a video with a frame missing. `compileProject`/`compileSnapshot` also take an optional `should_cancel` callback, polled between snapshots and before encoding (cooperative cancel for the async job API). `compileSnapshot` runs the action list for one snapshot and is also called directly by the web server to recompile a single commit; both entry points build their pipeline through `create_and_init_actions()`. Workdirs are keyed by `threading.get_ident()`, so a worker reuses (and mutates) one checkout across snapshots — actions must not assume a clean tree beyond what `git reset --hard` gives them.

**Reporter** (`reporter.py`) — the pipeline's only output channel. `TerminalReporter` drives an `alive_bar`; `WebReporter` emits `stage` / `add_progress` / `set_progress` / `log` over Socket.IO; `JobReporter` does the same but tags every event with a job id and records the latest stage/progress onto the `Job` so a polling client can read it. Never `print()` progress from an action.

**webserver.py / webui** — REST under `/api/projects/...` plus Socket.IO push. Renders run as async jobs: `POST /api/projects/<name>/jobs` starts one on a Socket.IO background task and returns a job id (202); `GET /api/jobs/<id>` polls status/progress; `DELETE /api/jobs/<id>` cancels cooperatively. `JobManager` (`jobs.py`) is the in-process registry and rejects a second concurrent render for one project (409). Job/CORS origins default to the Vite dev origin (override with `TEX_TIMELAPSE_CORS_ORIGINS`). `WebServer.run()` passes `allow_unsafe_werkzeug=True` — without eventlet/gevent, Flask-SocketIO ≥5 otherwise refuses to start the dev server. On the client, `src/models/ui-state.ts` is the store: RxJS `BehaviorSubject`s for the current project/snapshot, updated both by fetches and by incoming socket events. Pages live in `src/pages/`, feature components in `src/features/`, and `src/components/ui/` is generated shadcn/ui — don't hand-edit it.

## Gotchas

- `snapshots.yaml` is loaded with `yaml.CBaseLoader`, so **every value comes back as a string** — always cast when reading snapshot fields. Config is no longer like this: `config.py` defines a `Config` dataclass built via `Config.from_dict()`, which coerces once at load, so downstream code can rely on real `int`/`float`/`bool`/`str`. The coercion is needed because `project.yaml` keeps whatever type was written and the web UI historically POSTed `e.target.value` strings for numeric fields. Note the bool rule: `'false'`, `'False'`, `'0'`, `''` are False, every other string is True — plain `bool('false')` would be `True`.
- The action pipeline is defined **once** in `core/actions/__init__.py` (`ACTION_CLASSES`, `create_actions()`, `create_and_init_actions()`, `get_stage_names()`). Add a new stage there and every call site picks it up. It used to be duplicated four times, and a stage was already missed once as a result.
- `Action.init()` is called exactly once, in the calling thread, before the pool fans out — never from a worker. After init, treat `Action` instances as read-only: they are shared across threads.
- **PDFium is not thread-safe.** Every `pypdfium2` call must hold `PDFIUM_LOCK` (`core/pdfium_lock.py`). Without it, concurrent rendering segfaults the interpreter (exit 139) on roughly two runs in three.
- ffmpeg globs `frames/*.png`, so a dropped frame shifts the video rather than erroring. `compileProject` aborts before encoding if any snapshot ended `FAILED` (raising with the failing shas), unless `allowPartialRender: true` opts into encoding whatever succeeded. Note this is a status check *after* the loop, not an exception propagating out of `compileSnapshot` — that function catches action failures and returns a `FAILED`-status snapshot rather than raising.
- `README.md` documents the old flag-based CLI (`tex-timelapse.py main.tex --rows ...`) and predates the project/subcommand model. Treat `tex-timelapse.py` and `default_config.yaml` as the source of truth; `todo.txt` tracks the actual roadmap.
- On this WSL checkout, `mypy` crashes with a sqlite `unable to open database file` error because `.mypy_cache` lives on the `/mnt/s` drvfs mount. Pass `--cache-dir` pointing somewhere on the Linux filesystem.
- The web UI cannot be built with the Node on this machine (v12; Vite 5 needs 18+). `bun` 1.3.9 works as a stand-in, but note `bun x tsc` re-enters Node via the shebang — run the JS directly instead: `bun node_modules/typescript/lib/tsc.js --noEmit` and `bun node_modules/vite/bin/vite.js build`. npm remains the project standard; `bun.lock` is gitignored.
- Shell-outs must stay POSIX-portable — no GNU-only flags. `find -wholename` and the `grep -r` scans were removed for exactly this reason (they broke on macOS); prefer `pathlib`/`re` over spawning `find`/`grep`.
