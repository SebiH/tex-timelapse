
import os
from .job import Job
from ..project import Project
from ..snapshot import Snapshot, SnapshotStatus

class PdfToImageJob(Job):
    def getName(self) -> str:
        return 'PDF to Image'

    def init(self, project: Project) -> None:
        pass

    def cleanup(self) -> None:
        pass

    def run(self, snapshot: Snapshot) -> SnapshotStatus:
        os.makedirs(f'{snapshot.getWorkDir()}/images', exist_ok=True)

        pdfFile = snapshot.main_tex_file[:-4] + '.pdf'
        cmd = f'pdftoppm -png latex/{pdfFile} images/page'
        snapshot.execute(cmd)

        return SnapshotStatus.COMPLETED
