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
        self.project_img_dir = f'{project.projectFolder}/images'
        pass

    def cleanup(self) -> None:
        pass

    def run(self, snapshot: Snapshot) -> str:
        # reset folder
        snapshot_img_dir = f'{snapshot.getWorkDir()}/images'
        rmtree(snapshot_img_dir, ignore_errors=True)
        os.makedirs(snapshot_img_dir, exist_ok=True)

        pdfFile = snapshot.main_tex_file[:-4] + '.pdf'
        cmd = f'pdftoppm -jpeg {pdfFile} images/page'
        snapshot.execute_cmd(cmd)


        # move images
        img_save_dir = f'{self.project_img_dir}/{snapshot.commit_sha}'
        os.makedirs(img_save_dir, exist_ok=True)
        os.rename(snapshot_img_dir, img_save_dir)

        # save pages for use in the webserver / later steps
        snapshot.pages = [filename for filename in glob(f'{img_save_dir}/*.jpg')]

        return SnapshotStatus.COMPLETED

    def reset(self, snapshot: Snapshot) -> None:
        snapshot.pages = []
        # rmtree(self.img_dir, ignore_errors=True)
