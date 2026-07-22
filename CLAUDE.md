# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Turns the git history of a LaTeX project into a timelapse video. Each commit becomes a "snapshot": the repo is reset to that commit, compiled to PDF, rasterized to page images, and tiled into one grid frame. All frames are then encoded with ffmpeg. Changed regions are highlighted by mapping `git diff` line numbers to PDF coordinates via synctex.

Two frontends over the same pipeline: a CLI (`tex-timelapse.py`) and a Flask + Socket.IO server driving a React web UI (`webui/`).

## Commands

Python (run from repo root — paths like `./projects` and `./default_config.yaml` are relative to CWD):

```bash
pip install -r requirements.txt
python tex-timelapse.py init <name> <source.zip>   # only .zip sources are supported
python tex-timelapse.py run <name> <output>        # output = mp4 basename
python tex-timelapse.py list
python tex-timelapse.py server                     # Flask on :5000
mypy tex_timelapse                                 # typed codebase, no config file
```

Web UI (`webui/`, Vite + React 18 + shadcn/ui + Tailwind):

```bash
npm install
npm run dev      # :5173, proxies /api and /socket.io to localhost:5000
npm run build    # tsc && vite build
npm run lint
```

The dev server proxy is the only wiring between the two halves — Flask does **not** serve the built web UI, and the Dockerfile does not build it. Running the UI means running `python tex-timelapse.py server` and `npm run dev` side by side.

There are no tests.

## Architecture

**Project** (`project.py`) — a directory under `projects/<slugified-name>/` holding everything:

```
project.yaml      name + config (copied from default_config.yaml at init)
snapshots.yaml    per-commit state, the pipeline's resume/cache file
source/           unpacked zip, must contain .git
workdir/<tid>/    scratch checkouts, one per worker thread, deleted after a run
thumbnails/<sha>/ 600px page previews for the web UI
frames/           frame_%09d.png, the video's input
output/           <output>.mp4
```

**Snapshot** (`snapshot.py`) — one commit. Carries `commit_sha`, `index` (frame ordering), `status`, per-action `jobs` status, and the data actions pass to each other (`main_tex_file`, `includes`, `gitDiff`, `pages`, `changed_pages`). `execute_cmd()` shells out with `cwd` set to the snapshot's workdir; every action uses it rather than `subprocess` directly.

**Action** (`actions/action.py`) — pipeline stage with `init(project)` / `run(snapshot) -> SnapshotStatus` / `cleanup()` / `reset(snapshot)`. Order matters, each stage consumes the previous stage's fields on the snapshot:

1. `InitRepoAction` — `git reset --hard <sha>`, finds the main `.tex` (first file containing `\begin{document}`), walks `\include`/`\input`/`\addbibresource`/`\includegraphics` to build `includes`, stores `git diff --unified=0` per included file.
2. `ReplaceTextAction` — applies `text_replacements` from config (workaround for characters that break the compiler) and strips `\includeonly`.
3. `CompileLatexAction` — lualatex → biber → lualatex ×2, then converts diff line numbers to page coordinates with `synctex view`, writing `changed_pages`.
4. `PdfToImageAction` — `pdftoppm` for full-size pages (`pages`) and thumbnails.
5. `AssembleImageAction` — scales/blurs pages, draws the change overlays, tiles into `rows × columns`, writes `frames/frame_<index>.png`.

**compiler.py** — `compileProject` fans snapshots out over a module-level `ThreadPoolExecutor` (`setThreads()` to resize), then runs ffmpeg over `frames/*.png`. `compileSnapshot` runs the action list for one snapshot and is also called directly by the web server to recompile a single commit. Workdirs are keyed by `threading.get_ident()`, so a worker reuses (and mutates) one checkout across snapshots — actions must not assume a clean tree beyond what `git reset --hard` gives them.

**Reporter** (`reporter.py`) — the pipeline's only output channel. `TerminalReporter` drives an `alive_bar`; `WebReporter` emits `stage` / `add_progress` / `set_progress` / `log` over Socket.IO. Never `print()` progress from an action.

**webserver.py / webui** — REST under `/api/projects/...` plus Socket.IO push. On the client, `src/models/ui-state.ts` is the store: RxJS `BehaviorSubject`s for the current project/snapshot, updated both by fetches and by incoming socket events. Pages live in `src/pages/`, feature components in `src/features/`, and `src/components/ui/` is generated shadcn/ui — don't hand-edit it.

## Gotchas

- `snapshots.yaml` is loaded with `yaml.CBaseLoader`, so **every value comes back as a string**. Config values are likewise strings once round-tripped through `project.yaml` (see `projects/sample/project.yaml`: `rows: '1'`). Always cast (`int(...)`, `float(...)`, and note `bool('false')` is `True`) when reading config or snapshot fields.
- The action list is duplicated in `tex-timelapse.py:runProject` and twice in `webserver.py`. A new action must be added to all of them.
- ffmpeg globs `frames/*.png`, so a failed snapshot silently drops a frame rather than erroring.
- `config['latexCmd']` is read by `CompileLatexAction.init` but unused — the compile commands are hardcoded to lualatex/biber.
- `run --stage` compares an `int` against `action.getName()` (a string), so it never matches and the flag is currently a no-op.
- `README.md` documents the old flag-based CLI (`tex-timelapse.py main.tex --rows ...`) and predates the project/subcommand model. Treat `tex-timelapse.py` and `default_config.yaml` as the source of truth; `todo.txt` tracks the actual roadmap.
