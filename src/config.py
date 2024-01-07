import datetime
from typing import  TypedDict

class Config(TypedDict):
    sourceFolder: str
    mainTexFile: str

    rows: int
    columns: int
    blur: float
    highlightChanges: bool

    useMultithreading: bool
    workers: int # TODO: -1 should set to cpu count

    startCommit: str
    endCommit: str
    # startDate: datetime
    # endDate: datetime


    crop: bool
    cropTwoPage: bool
    cropLeft: int
    cropRight: int
    cropTop: int
    cropBottom: int
    cropAltLeft: int
    cropAltRight: int
    cropAltTop: int
    cropAltBottom: int

    # TODO: maybe change to latexMode: pdflatex | luaLaTeX | xelatex...?
    latexCmd: str

    overleafProjectId: str
    overleafAuthToken: str
