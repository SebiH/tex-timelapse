FROM alpine:3.17

RUN apk update
RUN apk upgrade

# Install LaTeX
WORKDIR /latex/
RUN apk add --no-cache perl wget
RUN wget http://mirror.ctan.org/systems/texlive/tlnet/install-tl-unx.tar.gz
RUN tar -xzf install-tl-unx.tar.gz
RUN cd install-tl-20* && \
  echo "selected_scheme scheme-small" > install.profile && \
  echo "tlpdbopt_install_docfiles 0" >> install.profile && \
  echo "tlpdbopt_install_srcfiles 0" >> install.profile && \
  echo "tlpdbopt_autobackup 0" >> install.profile && \
  echo "tlpdbopt_sys_bin /usr/bin" >> install.profile && \
  ./install-tl -profile install.profile \
  && cd .. && rm -rf install-tl*
ENV PATH="$PATH:/usr/local/texlive/2024/bin/x86_64-linuxmusl/"
RUN tlmgr path add
# Install fonts
RUN tlmgr install cm-super

# Set up non-python dependencies
RUN apk --no-cache add \
    python3 \
    py3-numpy \
    git \
    ffmpeg \
    # for pdftopppm
    poppler-utils

# latexmk doesn't seem to be available via apk?
RUN tlmgr install latexmk

# Trust all git repos to avoid any errors
RUN git config --global --add safe.directory '*'

# Set up python
ENV PYTHONUNBUFFERED=1
# Symlink python3 -> python, as some commands (e.g., texliveonfly) use python
RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools

WORKDIR /tex-timelapse/

COPY requirements.txt .
RUN pip install -r requirements.txt

# Set up texliveonfly for auto installation of latex packages
RUN tlmgr install texliveonfly

COPY tex-timelapse.py .
COPY tex_timelapse/ .

# Finish image
ENTRYPOINT [ "python", "tex-timelapse.py" ]
CMD [ "--help" ]
