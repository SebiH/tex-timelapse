FROM python:3.11

WORKDIR /visualizer/

# Set up non-python dependencies
RUN apt-get update
RUN apt-get install -y \
    ffmpeg \
    # for pdftopng
    poppler-utils \
    # latex
    texlive

# Set up python
COPY generate.py .
COPY requirements.txt .
RUN pip install -r requirements.txt

# Finish image
ENTRYPOINT [ "python", "generate.py" ]
CMD [ "--help" ]

