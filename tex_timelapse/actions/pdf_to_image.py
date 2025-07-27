from glob import glob
import os
from shutil import rmtree
from tex_timelapse.actions.action import Action
from tex_timelapse.project import Project
from tex_timelapse.snapshot import Snapshot, SnapshotStatus

class PdfToImageAction(Action):
    def getName(self) -> str:
        return 'PDF to Image'

    def init(self, project: Project) -> None:
        self.project_thumbnail_dir = f'{project.projectFolder}/thumbnails'
        pass

    def cleanup(self) -> None:
        pass

    def run(self, snapshot: Snapshot) -> str:
        # reset folder
        snapshot_img_dir = f'{snapshot.getWorkDir()}/images'
        rmtree(snapshot_img_dir, ignore_errors=True)
        os.makedirs(snapshot_img_dir, exist_ok=True)

        # convert PDF to images
        pdfFile = snapshot.main_tex_file[:-4] + '.pdf'
        cmd = f'pdftoppm -jpeg {pdfFile} images/page'
        snapshot.execute_cmd(cmd)


        # generate thumbnails for web UI
        thumbnail_dir = f'{snapshot.getWorkDir()}/thumbnails'
        rmtree(thumbnail_dir, ignore_errors=True)
        os.makedirs(thumbnail_dir, exist_ok=True)

        cmd = f'pdftoppm -jpeg -scale-to 300 {pdfFile} thumbnails/page'
        snapshot.execute_cmd(cmd)

        # move thumbnails
        thumbnail_save_dir = f'{self.project_thumbnail_dir}/{snapshot.commit_sha}'
        rmtree(thumbnail_save_dir, ignore_errors=True)
        os.makedirs(thumbnail_save_dir, exist_ok=True)
        os.rename(thumbnail_dir, thumbnail_save_dir)

        # save pages for use in the webserver / later steps
        snapshot.pages = [filename for filename in glob(f'{snapshot_img_dir}/*.jpg')]

        return SnapshotStatus.COMPLETED

    def reset(self, snapshot: Snapshot) -> None:
        snapshot.pages = []
        rmtree(f'{self.project_thumbnail_dir}/{snapshot.commit_sha}', ignore_errors=True)
