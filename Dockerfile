# syntax=docker/dockerfile:1
#
# Three build targets live in this one file:
#   webui-builder  - compiles the React app (intermediate stage only)
#   webui          - nginx serving webui/dist + reverse-proxying /api and
#                    /socket.io to the "app" target (see docker/nginx.conf)
#   app            - the actual tex-timelapse CLI / server (default target)
#
# docker-compose.yml builds both "app" and "webui" as separate services.
# A plain `docker build .` (no --target) builds "app", since it is last.


########################################################################
# Stage: webui-builder
# Builds the Vite/React app. Node 20, because Vite 5 requires Node >=18.
########################################################################
FROM node:20-slim AS webui-builder

WORKDIR /webui

# Install dependencies first so they're cached independently of source
# changes (package-lock.json only changes when dependencies change).
COPY webui/package.json webui/package-lock.json ./
RUN npm ci

# Now bring in the rest of the source and build.
COPY webui/ ./
RUN npm run build
# -> /webui/dist now holds the production build (static HTML/JS/CSS).


########################################################################
# Stage: webui
# Serves the built web UI. Flask does NOT serve webui/dist itself (see
# CLAUDE.md / docker/nginx.conf) - this is a stand-in static server until
# a follow-up wires Flask to serve the build directly. Kept as its own
# target so it can be built/run independently of the Python app image.
########################################################################
FROM nginx:1.27-alpine AS webui

COPY --from=webui-builder /webui/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf


########################################################################
# Stage: app
# The Python CLI/server plus a full-ish TeX Live install.
#
# Base image: debian-slim rather than alpine. numpy/Pillow/pypdfium2 ship
# manylinux (glibc) wheels; on alpine/musl there either are no matching
# wheels (forcing a slow from-source compile with extra -dev packages) or
# subtly different runtime behaviour. Debian-slim trades a somewhat larger
# base for "pip install just works" and is the safer default for an image
# that has to compile arbitrary users' LaTeX projects reliably.
########################################################################
FROM python:3.11-slim-bookworm AS app

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# --- OS-level dependencies -------------------------------------------------
# perl/wget: needed to fetch and run TeX Live's installer.
# ca-certificates: TLS for the wget below.
# git: the pipeline shells out to git directly (InitRepoAction and friends).
# ffmpeg: encodes the final timelapse video.
# fontconfig: lualatex's luaotfload font loader queries fontconfig.
# Deliberately NOT installing poppler-utils/pdftoppm: PDF rasterisation
# goes through the pypdfium2 Python package now (bundled binary, no system
# package needed) - see requirements.txt / actions/pdf_to_image.py.
RUN apt-get update && apt-get install -y --no-install-recommends \
        perl \
        wget \
        ca-certificates \
        git \
        ffmpeg \
        fontconfig \
    && rm -rf /var/lib/apt/lists/*

# --- TeX Live ---------------------------------------------------------------
# Installed via CTAN's network installer rather than apt's texlive package
# (Debian's is often a stale snapshot) or texlive/texlive (a much larger
# image we don't need as our base since we already build our own Python
# layer on top).
#
# Scheme: "scheme-small" (basic LaTeX + recommended fonts/packages), not
# scheme-full. scheme-full is multiple GB and mostly unused for a given
# document. Missing packages are instead pulled on demand at compile time
# by texliveonfly, which CompileLatexAction already invokes before every
# compile - so scheme-small + texliveonfly gives most of scheme-full's
# coverage without baking every CTAN package into the image. The trade-off:
# the very first compile of a document needing an uncommon package will be
# slower (or - if network access is unavailable at runtime - fail), and a
# few binaries that texliveonfly can't retroactively add (biber, latexmk)
# must be pre-installed explicitly, which is why they're listed below.
WORKDIR /tmp/texlive-install
RUN wget https://mirror.ctan.org/systems/texlive/tlnet/install-tl-unx.tar.gz \
    && tar -xzf install-tl-unx.tar.gz \
    && cd install-tl-20* \
    && echo "selected_scheme scheme-small" > install.profile \
    && echo "tlpdbopt_install_docfiles 0" >> install.profile \
    && echo "tlpdbopt_install_srcfiles 0" >> install.profile \
    && echo "tlpdbopt_autobackup 0" >> install.profile \
    && echo "tlpdbopt_sys_bin /usr/bin" >> install.profile \
    && ./install-tl -profile install.profile \
    && cd / && rm -rf /tmp/texlive-install
# WORKDIR was /tmp/texlive-install, which the line above just deleted -
# reset it before any further RUN tries to chdir into it.
WORKDIR /tex-timelapse

# `tlmgr path add` symlinks every installed binary into tlpdbopt_sys_bin
# (/usr/bin, set above) using whatever the *actual* installed year's
# directory is (/usr/local/texlive/<YEAR>/bin/<arch>/). This is what
# derives the path instead of a hardcoded year: no ENV PATH edit is needed
# or should be added here, since a fixed year will eventually stop matching
# what install-tl actually installs (it always installs the current
# release).
RUN tlmgr path add

# Packages/binaries not guaranteed by scheme-small, and which texliveonfly
# cannot retroactively install because they're missing *binaries* rather
# than missing .sty/.cls files it detects from a compile log:
#   - latexmk: the configured latexCmd (see default_config.yaml)
#   - biber: bibliography backend used by CompileLatexAction
#   - cm-super: Type1 fonts, avoids blurry PDF-to-image output for bitmap fonts
#   - texliveonfly: invoked by CompileLatexAction itself before every compile
RUN tlmgr install latexmk biber cm-super texliveonfly

# The app runs `git reset --hard`/`git diff` etc. against repos copied in
# at init time, which git refuses to touch by default unless they're
# explicitly trusted. --system (not --global) so this applies regardless
# of which user runs the container (see non-root user below).
RUN git config --system --add safe.directory '*'

# --- Application: install the backend package --------------------------
# The backend is a packaged project under backend/ (backend/pyproject.toml);
# installing it pulls in the pinned runtime deps and puts the `tex-timelapse`
# console script on PATH. default_config.yaml travels inside the package
# (declared as package-data), so no separate copy is needed.
#
# Not split into a deps-cache-then-source layer: pip needs the package source
# to resolve its own metadata, and on this image the TeX Live layer above
# dwarfs the pip install anyway, so the extra caching machinery isn't worth
# it. Non-editable install (production image): src edits mean a rebuild.
# (WORKDIR /tex-timelapse was already set above, after the TeX Live install.)
COPY backend/ ./backend/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ./backend

# --- Non-root runtime user -----------------------------------------------
# projects/ and uploads/ are where the app writes at runtime (see
# docker-compose.yml volumes); create them up front so they're owned by
# the app user rather than root before anything is ever mounted over them.
#
# UID/GID are build args (default 1000, the common single-user-Linux
# default) so they can be overridden at build time to match the host user
# that owns the bind-mounted ./projects and ./uploads directories, e.g.:
#   docker build --build-arg APP_UID=$(id -u) --build-arg APP_GID=$(id -g) .
# Mismatched ids will otherwise show up as permission-denied errors when
# the container tries to write into those host directories.
ARG APP_UID=1000
ARG APP_GID=1000
RUN groupadd --gid "${APP_GID}" app \
    && useradd --uid "${APP_UID}" --gid app --create-home --shell /bin/bash app \
    && mkdir -p /tex-timelapse/projects /tex-timelapse/uploads \
    && chown -R app:app /tex-timelapse

# scheme-small deliberately relies on texliveonfly pulling missing packages at
# compile time, but tlmgr writes into the TeX Live tree - which root owns. As
# the unprivileged app user those installs would fail (silently: the call is
# ignore_error=True), and the compile would then fail on the missing package.
# Hand the tree to the app user so on-demand installation actually works.
# This costs an extra layer roughly the size of the TeX Live install; the
# alternative is baking in scheme-full and dropping texliveonfly entirely.
RUN chown -R app:app /usr/local/texlive

USER app

# The `tex-timelapse` console script (from backend/pyproject.toml's
# [project.scripts]) runs with WORKDIR /tex-timelapse, so projects_root()'s
# CWD-relative default resolves to /tex-timelapse/projects - matching the
# compose volume mount. compose appends e.g. `server --host 0.0.0.0`.
ENTRYPOINT [ "tex-timelapse" ]
CMD [ "--help" ]
