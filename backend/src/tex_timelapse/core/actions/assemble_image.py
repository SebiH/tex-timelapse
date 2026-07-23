import os
from typing import List, Tuple
from tex_timelapse.core.actions.action import Action
from tex_timelapse.core.config import Config
from tex_timelapse.core.project import Project
from tex_timelapse.core.snapshot import Snapshot, SnapshotStatus
from PIL import Image, ImageFilter, ImageDraw
import numpy as np
import pypdfium2 as pdfium  # type: ignore[import-untyped]  # no py.typed marker/stubs published
from tex_timelapse.core.pdfium_lock import PDFIUM_LOCK

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


def pad_or_trim_images(images: List[Image.Image], target_count: int, image_size: Tuple[int, int]) -> List[Image.Image]:
    """Extend `images` with blank white frames until there are exactly
    `target_count` of them, or drop trailing entries if there are already
    more than that many. Mutates and returns `images`.

    Extracted from AssembleImageAction.run for testability - no behaviour
    change. Assumes `images` is already non-empty; that check stays in
    run() because it needs the snapshot's commit sha for the error message.
    """
    while len(images) < target_count:
        images.append(Image.new('RGB', image_size, color='white'))
    while len(images) > target_count:
        images.pop()
    return images


def crop_box_for_page(config: Config, page_index: int, width: int, height: int) -> Tuple[int, int, int, int]:
    """The PIL crop box (left, top, right, bottom) for one rendered page.

    Insets are pixel counts from each edge of the full-resolution (150-DPI)
    page image, applied before any fit-scale/resize. They come straight
    from config.crop{Left,Right,Top,Bottom} - or, when config.cropTwoPage is
    on, from the cropAlt* variants for odd (0-based) page_index - modelling
    a mirrored two-page layout (e.g. the ACM single-column template) where
    even and odd pages have swapped margins.

    Returns the full, uncropped box (0, 0, width, height) - a no-op crop -
    when cropping is disabled, or defensively when the configured insets
    would leave a zero or negative-size image behind. Never raises, never
    produces a degenerate crop.
    """
    if not config.crop:
        return (0, 0, width, height)

    if config.cropTwoPage and page_index % 2 != 0:
        left, right, top, bottom = config.cropAltLeft, config.cropAltRight, config.cropAltTop, config.cropAltBottom
    else:
        left, right, top, bottom = config.cropLeft, config.cropRight, config.cropTop, config.cropBottom

    if left + right >= width or top + bottom >= height:
        return (0, 0, width, height)

    return (left, top, width - right, height - bottom)


class AssembleImageAction(Action):
    def getName(self) -> str:
        return 'Assemble Image'

    def init(self, project: Project) -> None:
        self.config = project.config
        self.blur = project.config.blur
        self.rows = project.config.rows
        self.columns = project.config.columns
        self.highlightChanges = project.config.highlightChanges
        self.project_img_dir = f'{project.projectFolder}/frames'

        os.makedirs(self.project_img_dir, exist_ok=True)

    def cleanup(self) -> None:
        pass

    def run(self, snapshot: Snapshot) -> str:
        workDir = snapshot.getWorkDir()
        # snapshot.pages only stores basenames (see PdfToImageAction) - resolve
        # them against the workdir's images folder to get real paths.
        rawImages = sorted(f'{workDir}/images/{page}' for page in snapshot.pages)

        if len(rawImages) == 0:
            raise Exception(f'No images found for {snapshot.commit_sha}')

        rawOpened = [Image.open(p) for p in rawImages]

        # Pages are assumed to share one physical size (true for any
        # normal LaTeX document) - the crop box is computed against page
        # 0's raw dimensions and reused for every page's own parity.
        raw_width, raw_height = rawOpened[0].size

        # Per-page crop boxes in raw (150-DPI) pixel space. crop_box_for_page
        # already returns the full, uncropped box when cropping is off, so
        # everything below can treat "cropped" and "uncropped" uniformly.
        crop_boxes = [crop_box_for_page(self.config, i, raw_width, raw_height) for i in range(len(rawOpened))]

        # Reference dimensions for the 1920x1080 fit-scale: the cropped size
        # of page 0. Two-page crops can legitimately size even/odd pages
        # differently (asymmetric margins); this mirrors the pre-crop
        # code's practice of sizing the whole grid off image 0.
        ref_left, ref_top, ref_right, ref_bottom = crop_boxes[0]
        ref_width, ref_height = ref_right - ref_left, ref_bottom - ref_top

        # Check if the resulting image size is too large and downscale as needed
        scale = 1.0
        if ref_width * self.columns > 1920 or ref_height * self.rows > 1080:
            scale = min(1920.0 / (ref_width * self.columns), 1080.0 / (ref_height * self.rows))

        image_size = (int(ref_width * scale), int(ref_height * scale))
        image_width, image_height = image_size

        images = []
        for rawImg, box in zip(rawOpened, crop_boxes):
            cropped = rawImg.crop(box)
            target_size = (int((box[2] - box[0]) * scale), int((box[3] - box[1]) * scale))
            resized = cropped.resize(target_size, Image.Resampling.NEAREST)
            if self.blur > 0:
                resized = resized.filter(ImageFilter.GaussianBlur(self.blur))
            images.append(resized)

        # Fill array with empty images if there are not enough pages, or trim
        # if there are too many to fit in the frame
        images = pad_or_trim_images(images, self.rows * self.columns, image_size)

        # images for drawing overlays
        drawImages = []
        for i in range(len(images)):
            drawImages.append(Image.new('RGBA', images[i].size, '#FFFFFF00'))

        if self.highlightChanges:

            texFile = snapshot.main_tex_file
            pdfFile = texFile[:-4] + '.pdf'
            pdf_size = self.get_pdf_dimensions(f'{workDir}/{pdfFile}')

            # Where a point would land if the FULL (uncropped) page were
            # rendered at this run's fit-scale. Every page's crop offset is
            # expressed in these same units so it can be subtracted
            # directly from the h/v this yields below.
            raw_scaled_size = (raw_width * scale, raw_height * scale)

            # highlight entire pages first
            for synctexInfo in snapshot.changed_pages:
                page_num = int(synctexInfo['page'])
                if page_num and page_num <= len(drawImages):
                    drawImages[page_num - 1] = Image.new('RGBA', images[page_num - 1].size, '#A3BE8C44')

            # draw in more detailed changes
            for synctexInfo in snapshot.changed_pages:
                page_num = int(synctexInfo['page'])
                # changed_pages is derived from git diff/synctex output, not
                # necessarily bounded by the pages actually rendered - fall
                # back to page 0's crop for an out-of-range page number
                # rather than indexing off the end of crop_boxes.
                page_index = page_num - 1 if 0 < page_num <= len(crop_boxes) else 0

                x, y, h, v, W, H = self.convert_synctex_to_image_coords(pdf_size, raw_scaled_size, synctexInfo)

                # Shift from "full uncropped page" space into this page's
                # cropped local origin - the crop offset has to be scaled
                # the same way the page image itself was.
                crop_left, crop_top, _, _ = crop_boxes[page_index]
                h -= int(crop_left * scale)
                v -= int(crop_top * scale)

                page_size = images[page_index].size if page_index < len(images) else image_size
                page_width, page_height = page_size

                padding = page_width // 10

                # for webui - normalised to this page's own (cropped) size
                synctexInfo['x1'] = float(h - padding) / float(page_width)
                synctexInfo['y1'] = float(v - padding) / float(page_height)
                synctexInfo['x2'] = float(h + W + padding) / float(page_width)
                synctexInfo['y2'] = float(v + H + padding) / float(page_height)

                if not page_num or page_num > len(drawImages):
                    continue

                draw = ImageDraw.Draw(drawImages[page_num - 1])
                draw.rectangle((h - padding, v - padding, h + W + padding, v + H + padding), fill = '#81A1C144')


            # combine overlays
            for i in range(len(images)):
                images[i] = Image.alpha_composite(images[i].convert('RGBA'), drawImages[i])

        img = pil_grid(images, self.columns)
        img.save(f'{self.project_img_dir}/frame_{snapshot.index:09d}.png')

        return SnapshotStatus.COMPLETED

    def reset(self, snapshot: Snapshot) -> None:
        try:
            image_path = f'{self.project_img_dir}/frame_{snapshot.index:09d}.png'
            os.remove(image_path)
        except:  # noqa: E722
            pass



    def get_pdf_dimensions(self, pdf_path: str) -> Tuple[float, float]:
        # Serialised against every other pdfium call - PDFium is not
        # thread-safe and snapshots are processed concurrently. See
        # pdfium_lock.py.
        with PDFIUM_LOCK:
            doc = pdfium.PdfDocument(pdf_path)
            try:
                page = doc.get_page(0) # TODO: pass page number as argument
                try:
                    pdf_width, pdf_height = page.get_size()
                finally:
                    page.close()
            finally:
                doc.close()
        return float(pdf_width), float(pdf_height)

    def get_image_dimensions(self, image_path: str) -> Tuple[float, float]:
        with Image.open(image_path) as img:
            img_width, img_height = img.size
        return img_width, img_height

    def convert_synctex_to_image_coords(self, pdf_size: Tuple[float, float], image_size: Tuple[float, float], synctex_coords):
        # Assume pdf_page_size is (width, height) in points (1/72 inch)
        # Assume image_size is (width, height) in pixels
        pdf_width, pdf_height = pdf_size
        image_width, image_height = image_size

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
