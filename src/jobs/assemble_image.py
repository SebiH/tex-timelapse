import os
from .job import Job
from ..project import Project
from ..snapshot import Snapshot, SnapshotStatus
from PIL import Image, ImageFilter
from glob import glob
import numpy as np

# see https://stackoverflow.com/a/46877433/4090817
def pil_grid(images, max_horiz=np.iinfo(int).max):
    n_images = len(images)
    n_horiz = min(n_images, max_horiz)
    h_sizes, v_sizes = [0] * n_horiz, [0] * ((n_images // n_horiz) + (1 if n_images % n_horiz > 0 else 0))
    for i, im in enumerate(images):
        h, v = i % n_horiz, i // n_horiz
        h_sizes[h] = max(h_sizes[h], im.size[0])
        v_sizes[v] = max(v_sizes[v], im.size[1])
    h_sizes, v_sizes = np.cumsum([0] + h_sizes), np.cumsum([0] + v_sizes)
    im_grid = Image.new('RGB', (h_sizes[-1], v_sizes[-1]), color='white')
    for i, im in enumerate(images):
        im_grid.paste(im, (h_sizes[i % n_horiz], v_sizes[i // n_horiz]))
    return im_grid


class AssembleImageJob(Job):
    def getName(self) -> str:
        return "Assemble Image"

    def init(self, project: Project) -> None:
        os.makedirs(f'{project.projectFolder}/frames', exist_ok=True)

        self.blur = project.config['blur']
        self.rows = project.config['rows']
        self.columns = project.config['columns']
        self.highlightChanges = project.config['highlightChanges']
        pass

    def cleanup(self) -> None:
        pass

    def run(self, snapshot: Snapshot) -> SnapshotStatus:
        workDir = snapshot.getWorkDir()
        rawImages = sorted(glob(f'{workDir}/images/page-*.png'))

        if self.blur > 0:
            images = [Image.open(i).filter(ImageFilter.GaussianBlur(self.blur)) for i in rawImages]
        else:
            images = rawImages

        if (len(images) == 0):
            raise Exception(f'No images found for {snapshot.commit_sha}')

        # Fill array with empty images if there are not enough pages
        while (len(images) < self.rows * self.columns):
            images.append(Image.new('RGB', (1275, 1651), color='white'))
        # Remove unnecessary pages that wouldn't fit in the frame
        while ((len(images)) > self.rows * self.columns):
            images.pop()

        # Image crop - only works for ACM single column template
        # for i in range(len(images)):
        #     if i % 2 != 0:
        #         images[i] = images[i].crop((200, 130, 1150, 1380))
        #     else:
        #         images[i] = images[i].crop((130, 130, 1080, 1380))

        if self.highlightChanges:
            overlay = Image.new('RGBA', images[0].size, '#A3BE8C66')
            for page_num in snapshot.changed_pages:
                if page_num and int(page_num) <= len(images):
                    page_num = int(page_num)
                    img = images[page_num-1].convert('RGBA')
                    img = Image.alpha_composite(img, overlay)
                    images[page_num-1] = img

        img = pil_grid(images, self.columns)
        img.save(f'{snapshot.project_dir}/frames/frame_{snapshot.commit_date}.png')

        return SnapshotStatus.COMPLETED
