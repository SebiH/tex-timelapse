import os
from shutil import rmtree
from tex_timelapse.actions.action import Action
from tex_timelapse.project import Project
from tex_timelapse.snapshot import Snapshot, SnapshotStatus

class PdfToImageAction(Action):
    def getName(self) -> str:
        return 'PDF to Image'

    def init(self, project: Project) -> None:
        self.img_dir = f'{project.projectFolder}/images'
        pass

    def cleanup(self) -> None:
        pass

    def run(self, snapshot: Snapshot) -> str:
        os.makedirs(self.img_dir, exist_ok=True)

        pdfFile = snapshot.main_tex_file[:-4] + '.pdf'
        # create images folder
        os.makedirs(snapshot.getWorkDir() + '/images', exist_ok=True)

        cmd = f'pdftoppm -png {pdfFile} images/page'
        snapshot.execute(cmd)

        # save pages for use in the webserver
        images = snapshot.execute('find images/', ignore_error=True)
        snapshot.pages = [f"{snapshot.getWorkDir()}/{f}" for f in images.split('\n') if f.endswith('.png')]

        return SnapshotStatus.COMPLETED

    def reset(self, snapshot: Snapshot) -> None:
        snapshot.pages = []
        rmtree(self.img_dir, ignore_errors=True)
