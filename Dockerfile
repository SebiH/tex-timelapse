FROM python:3.11

WORKDIR /visualizer/

# Set up non-python dependencies
RUN apt-get update
RUN apt-get install -y \
    ffmpeg \
    # for pdftopng
    poppler-utils \
    # latex
    texlive-full \
    latexmk 

# Set up python
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY generate.py .

# Finish image
ENTRYPOINT [ "python", "generate.py" ]
CMD [ "--help" ]

