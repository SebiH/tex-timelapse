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
thumbnails/<sha>/ 300px page previews for the web UI
frames/           frame_%09d.png, the video's input
output/           <output>.mp4
```

**Snapshot** (`snapshot.py`) — one commit. Carries `commit_sha`, `index` (frame ordering), `status`, per-action `jobs` status, and the data actions pass to each other (`main_tex_file`, `includes`, `gitDiff`, `pages`, `changed_pages`). `execute_cmd()` shells out with `cwd` set to the snapshot's workdir; every action uses it rather than `subprocess` directly.

**Action** (`actions/action.py`) — pipeline stage with `init(project)` / `run(snapshot) -> SnapshotStatus` / `cleanup()` / `reset(snapshot)`. Order matters, each stage consumes the previous stage's fields on the snapshot:

1. `InitRepoAction` — `git reset --hard <sha>`, finds the main `.tex` (first file containing `\begin{document}`), walks `\include`/`\input`/`\addbibresource`/`\includegraphics` to build `includes`, stores `git diff --unified=0` per included file.
2. `ReplaceTextAction` — applies `text_replacements` from config (workaround for characters that break the compiler) and strips `\includeonly`.
3. `CompileLatexAction` — runs `texliveonfly` (to pull missing packages), then `config['latexCmd']` once. The default is `latexmk`, which internally handles reruns and the bibliography pass; a custom non-latexmk command gets a single pass only. Success is judged by whether a PDF appeared, not by exit code. Then converts diff line numbers to page coordinates with `synctex view`, writing `changed_pages`.
4. `PdfToImageAction` — renders each page once with `pypdfium2` at 150/72 scale (matching `pdftoppm`'s old 150 DPI output), saving full-size pages (`pages`) plus a Pillow-downscaled 300px thumbnail. Filenames keep `pdftoppm`'s zero-padding (`page-01.jpg`) because several plain lexicographic sorts depend on it.
5. `AssembleImageAction` — scales/blurs pages, draws the change overlays, tiles into `rows × columns`, writes `frames/frame_<index>.png`.

**compiler.py** — `compileProject` fans snapshots out over a module-level `ThreadPoolExecutor` (`setThreads()` to resize), then runs ffmpeg over `frames/*.png`. `compileSnapshot` runs the action list for one snapshot and is also called directly by the web server to recompile a single commit. Workdirs are keyed by `threading.get_ident()`, so a worker reuses (and mutates) one checkout across snapshots — actions must not assume a clean tree beyond what `git reset --hard` gives them.

**Reporter** (`reporter.py`) — the pipeline's only output channel. `TerminalReporter` drives an `alive_bar`; `WebReporter` emits `stage` / `add_progress` / `set_progress` / `log` over Socket.IO. Never `print()` progress from an action.

**webserver.py / webui** — REST under `/api/projects/...` plus Socket.IO push. On the client, `src/models/ui-state.ts` is the store: RxJS `BehaviorSubject`s for the current project/snapshot, updated both by fetches and by incoming socket events. Pages live in `src/pages/`, feature components in `src/features/`, and `src/components/ui/` is generated shadcn/ui — don't hand-edit it.

## Gotchas

- `snapshots.yaml` is loaded with `yaml.CBaseLoader`, so **every value comes back as a string**. `project.yaml` uses `safe_load`, so config values keep whatever type they were written with — and the web UI POSTs `e.target.value` **strings** for numeric fields like `rows`/`columns`/`framerate` while sliders POST numbers (see `projects/sample/project.yaml`: `rows: '1'`). Always cast (`int(...)`, `float(...)`, and note `bool('false')` is `True`) when reading config or snapshot fields.
- The action list is duplicated in `tex-timelapse.py:runProject` and three times in `webserver.py`. A new action must be added to all of them.
- ffmpeg globs `frames/*.png`, so a dropped frame shifts the video rather than erroring. `compileProject` now re-raises on failure so a broken run stops before encoding.
- `README.md` documents the old flag-based CLI (`tex-timelapse.py main.tex --rows ...`) and predates the project/subcommand model. Treat `tex-timelapse.py` and `default_config.yaml` as the source of truth; `todo.txt` tracks the actual roadmap.
- On this WSL checkout, `mypy` crashes with a sqlite `unable to open database file` error because `.mypy_cache` lives on the `/mnt/s` drvfs mount. Pass `--cache-dir` pointing somewhere on the Linux filesystem.
- The web UI cannot be built with the Node on this machine (v12; Vite 5 needs 18+). `bun` 1.3.9 works as a stand-in, but note `bun x tsc` re-enters Node via the shebang — run the JS directly instead: `bun node_modules/typescript/lib/tsc.js --noEmit` and `bun node_modules/vite/bin/vite.js build`. npm remains the project standard; `bun.lock` is gitignored.
- Shell-outs must stay POSIX-portable — no GNU-only flags. `find -wholename` and the `grep -r` scans were removed for exactly this reason (they broke on macOS); prefer `pathlib`/`re` over spawning `find`/`grep`.
