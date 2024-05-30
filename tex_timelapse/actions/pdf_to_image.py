import os
from shutil import rmtree
from tex_timelapse.actions.action import Action
from tex_timelapse.project import Project
from tex_timelapse.snapshot import Snapshot, SnapshotStatus

class PdfToImageAction(Action):
    def getName(self) -> str:
        return 'PDF to Image'

    def init(self, project: Project) -> None:
        pass

    def cleanup(self) -> None:
        pass

    def run(self, snapshot: Snapshot) -> str:
        os.makedirs(f'{snapshot.getWorkDir()}/images', exist_ok=True)

        pdfFile = snapshot.main_tex_file[:-4] + '.pdf'
        cmd = f'pdftoppm -png latex/{pdfFile} images/page'
        snapshot.execute(cmd)

        # save pages for use in the webserver
        images = snapshot.execute('find .', 'images', ignore_error=True)
        
        # since files are prefixed with ./, we remove the first two characters
        snapshot.pages = [f[2:] for f in images.split('\n') if f.endswith('.png')]

        return SnapshotStatus.COMPLETED

    def reset(self, snapshot: Snapshot) -> None:
        snapshot.pages = []
        rmtree(f'{snapshot.getWorkDir()}/images', ignore_errors=True)
