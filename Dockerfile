FROM pandoc/latex:3-alpine

WORKDIR /visualizer/

# Set up non-python dependencies
RUN apk --update --no-cache add \
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

COPY requirements.txt .
RUN pip install -r requirements.txt

# Set up texliveonfly for auto installation of latex packages
RUN tlmgr install texliveonfly

COPY generate.py .

# Finish image
ENTRYPOINT [ "python", "generate.py" ]
CMD [ "--help" ]
