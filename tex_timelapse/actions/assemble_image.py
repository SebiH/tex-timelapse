import os
from typing import Tuple
from tex_timelapse.actions.action import Action
from tex_timelapse.project import Project
from tex_timelapse.snapshot import Snapshot, SnapshotStatus
from PIL import Image, ImageFilter, ImageDraw
from glob import glob
import numpy as np
from PyPDF2 import PdfReader

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


class AssembleImageAction(Action):
    def getName(self) -> str:
        return 'Assemble Image'

    def init(self, project: Project) -> None:
        os.makedirs(f'{project.projectFolder}/frames', exist_ok=True)

        self.blur = float(project.config['blur'])
        self.rows = int(project.config['rows'])
        self.columns = int(project.config['columns'])
        self.highlightChanges = bool(project.config['highlightChanges'])
        pass

    def cleanup(self) -> None:
        pass

    def run(self, snapshot: Snapshot) -> str:
        workDir = snapshot.getWorkDir()
        rawImages = sorted(glob(f'{workDir}/images/page-*.png'))

        if self.blur > 0:
            images = [Image.open(i).filter(ImageFilter.GaussianBlur(self.blur)) for i in rawImages]
        else:
            images = [Image.open(i) for i in rawImages]

        if (len(images) == 0):
            raise Exception(f'No images found for {snapshot.commit_sha}')

        # Fill array with empty images if there are not enough pages
        while (len(images) < self.rows * self.columns):
            images.append(Image.new('RGB', (1275, 1651), color='white'))
        # Remove unnecessary pages that wouldn't fit in the frame
        while ((len(images)) > self.rows * self.columns):
            images.pop()

        # images for drawing overlays
        drawImages = []
        for i in range(len(images)):
            drawImages.append(Image.new('RGBA', images[i].size, '#FFFFFF00'))

        # Image crop - only works for ACM single column template
        # for i in range(len(images)):
        #     if i % 2 != 0:
        #         images[i] = images[i].crop((200, 130, 1150, 1380))
        #     else:
        #         images[i] = images[i].crop((130, 130, 1080, 1380))

        if self.highlightChanges:
            image_width, image_height = images[0].size

            # highlight entire pages first
            for synctexInfo in snapshot.changed_pages:
                page_num = int(synctexInfo['page'])
                if page_num and page_num <= len(drawImages):
                    drawImages[page_num - 1] = Image.new('RGBA', images[0].size, '#A3BE8C44')

            # draw in more detailed changes
            for synctexInfo in snapshot.changed_pages:
                page_num = int(synctexInfo['page'])
                texFile = snapshot.main_tex_file
                pdfFile = texFile[:-4] + '.pdf'

                x, y, h, v, W, H = self.convert_synctex_to_image_coords(f'{workDir}/latex/{pdfFile}', f'{workDir}/images/{snapshot.pages[page_num - 1]}', synctexInfo)

                padding = 25

                # for webui
                synctexInfo['x1'] = float(h - padding) / float(image_width)
                synctexInfo['y1'] = float(v - padding) / float(image_height)
                synctexInfo['x2'] = float(h + W + padding) / float(image_width)
                synctexInfo['y2'] = float(v + H + padding) / float(image_height)

                if not page_num or page_num > len(drawImages):
                    continue

                draw = ImageDraw.Draw(drawImages[page_num - 1])
                draw.rectangle((h - padding, v - padding, h + W + padding, v + H + padding), fill = '#81A1C144')


            # combine overlays
            for i in range(len(images)):
                images[i] = Image.alpha_composite(images[i].convert('RGBA'), drawImages[i])

        img = pil_grid(images, self.columns)
        img.save(f'{snapshot.project_dir}/frames/frame_{snapshot.commit_date}.png')

        return SnapshotStatus.COMPLETED

    def reset(self, snapshot: Snapshot) -> None:
        try:
            image_path = f'{snapshot.project_dir}/frames/frame_{snapshot.commit_date}.png'
            os.remove(image_path)
        except:  # noqa: E722
            pass



    def get_pdf_dimensions(self, pdf_path: str) -> Tuple[float, float]:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            page = reader.pages[0] # TODO: pass page number as argument
            media_box = page.mediabox
            pdf_width = media_box.right - media_box.left
            pdf_height = media_box.top - media_box.bottom
        return float(pdf_width), float(pdf_height)

    def get_image_dimensions(self, image_path: str) -> Tuple[float, float]:
        with Image.open(image_path) as img:
            img_width, img_height = img.size
        return img_width, img_height

    def convert_synctex_to_image_coords(self, pdf_path: str, image_path: str, synctex_coords):
        # Assume pdf_page_size is (width, height) in points (1/72 inch)
        # Assume image_size is (width, height) in pixels
        pdf_width, pdf_height = self.get_pdf_dimensions(pdf_path)
        image_width, image_height = self.get_image_dimensions(image_path)

        # Convert coordinates to image coordinates
        x_ratio = image_width / pdf_width
        y_ratio = image_height / pdf_height

        x = int(synctex_coords['x'] * x_ratio)
        y = image_height - int(synctex_coords['y'] * y_ratio)  # Invert y-coordinate
        h = int(synctex_coords['h'] * y_ratio)
        v = int(synctex_coords['v'] * x_ratio)
        W = int(synctex_coords['W'] * x_ratio)
        H = int(synctex_coords['H'] * y_ratio)

        return x, y, h, v, W, H
