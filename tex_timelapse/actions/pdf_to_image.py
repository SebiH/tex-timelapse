import os
from shutil import rmtree
import pypdfium2 as pdfium  # type: ignore[import-untyped]  # no py.typed marker/stubs published
from PIL import Image
from tex_timelapse.actions.action import Action
from tex_timelapse.project import Project
from tex_timelapse.snapshot import Snapshot, SnapshotStatus

# pdftoppm rasterises at 150 DPI by default, while pypdfium2 renders at a
# native 72 DPI (1 PDF point == 1 pixel at scale 1). Scale by 150/72 to
# reproduce the same output resolution as before.
RENDER_SCALE = 150.0 / 72.0

# Longest-side pixel size for web UI thumbnails (matches the previous
# `pdftoppm -scale-to 300` behaviour).
THUMBNAIL_MAX_SIDE = 300


class PdfToImageAction(Action):
    def getName(self) -> str:
        return 'PDF to Image'

    def init(self, project: Project) -> None:
        self.project_thumbnail_dir = f'{project.projectFolder}/thumbnails'
        pass

    def cleanup(self) -> None:
        pass

    def run(self, snapshot: Snapshot) -> str:
        # reset folders
        snapshot_img_dir = f'{snapshot.getWorkDir()}/images'
        rmtree(snapshot_img_dir, ignore_errors=True)
        os.makedirs(snapshot_img_dir, exist_ok=True)

        thumbnail_dir = f'{snapshot.getWorkDir()}/thumbnails'
        rmtree(thumbnail_dir, ignore_errors=True)
        os.makedirs(thumbnail_dir, exist_ok=True)

        pdfFile = snapshot.main_tex_file[:-4] + '.pdf'
        pdfPath = f'{snapshot.getWorkDir()}/{pdfFile}'

        # Render each page once with pypdfium2, then derive the thumbnail by
        # downscaling in Pillow, instead of rasterising twice with pdftoppm.
        pages = []
        doc = pdfium.PdfDocument(pdfPath)
        try:
            page_count = len(doc)
            # pdftoppm zero-pads its output filenames to the width of the
            # highest page number (e.g. page-01.jpg .. page-10.jpg for a
            # 10-page document). Reproduce that so plain string sort - used
            # both here, in AssembleImageAction, and in the web UI - keeps
            # pages in true numeric order regardless of page count.
            width = len(str(page_count))

            for i in range(page_count):
                page = doc.get_page(i)
                try:
                    bitmap = page.render(scale=RENDER_SCALE)
                    try:
                        image = bitmap.to_pil().convert('RGB')
                    finally:
                        bitmap.close()
                finally:
                    page.close()

                name = f'page-{i + 1:0{width}d}.jpg'
                image.save(f'{snapshot_img_dir}/{name}')

                # -scale-to N scales the longest side to N pixels, preserving
                # aspect ratio.
                img_width, img_height = image.size
                longest_side = max(img_width, img_height)
                ratio = THUMBNAIL_MAX_SIDE / longest_side
                thumb_size = (max(1, round(img_width * ratio)), max(1, round(img_height * ratio)))
                thumbnail = image.resize(thumb_size, Image.Resampling.LANCZOS)
                thumbnail.save(f'{thumbnail_dir}/{name}')

                pages.append(name)
        finally:
            doc.close()

        # move thumbnails
        thumbnail_save_dir = f'{self.project_thumbnail_dir}/{snapshot.commit_sha}'
        rmtree(thumbnail_save_dir, ignore_errors=True)
        os.makedirs(thumbnail_save_dir, exist_ok=True)
        os.rename(thumbnail_dir, thumbnail_save_dir)

        # save pages for use in the webserver / later steps
        # store bare basenames only: workdir (and thus the absolute paths) is
        # deleted after the run, so persisting absolute paths in snapshots.yaml
        # would leave dangling references.
        snapshot.pages = sorted(pages)

        return SnapshotStatus.COMPLETED

    def reset(self, snapshot: Snapshot) -> None:
        snapshot.pages = []
        rmtree(f'{self.project_thumbnail_dir}/{snapshot.commit_sha}', ignore_errors=True)
