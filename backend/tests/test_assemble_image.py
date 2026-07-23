"""Tests for tex_timelapse.core.actions.assemble_image's pure geometry helpers:
pil_grid, pad_or_trim_images, convert_synctex_to_image_coords, and
crop_box_for_page."""

import numpy as np
import pytest
from PIL import Image

from tex_timelapse.core.actions.assemble_image import (
    AssembleImageAction,
    crop_box_for_page,
    pad_or_trim_images,
    pil_grid,
)
from tex_timelapse.core.config import Config


def _solid(size, color=(255, 0, 0)):
    return Image.new('RGB', size, color=color)


# ---------------------------------------------------------------------------
# pil_grid
# ---------------------------------------------------------------------------

def test_pil_grid_single_row():
    images = [_solid((10, 20)), _solid((10, 20)), _solid((10, 20))]
    grid = pil_grid(images, max_horiz=3)
    assert grid.size == (30, 20)


def test_pil_grid_wraps_to_multiple_rows():
    images = [_solid((10, 10)) for _ in range(5)]
    grid = pil_grid(images, max_horiz=2)
    # 5 images at 2-per-row -> 3 rows, 2 columns
    assert grid.size == (20, 30)


def test_pil_grid_uses_max_dimension_per_row_and_column():
    # mismatched sizes: the grid cell for each row/column is the max size
    # of anything placed there (see h_sizes/v_sizes in the implementation).
    images = [_solid((10, 10)), _solid((20, 5))]
    grid = pil_grid(images, max_horiz=2)
    assert grid.size == (30, 10)


def test_pil_grid_default_max_horiz_is_single_row():
    images = [_solid((5, 5)) for _ in range(4)]
    grid = pil_grid(images)  # default max_horiz effectively unbounded
    assert grid.size == (20, 5)


def test_pil_grid_places_images_at_expected_offsets():
    images = [_solid((4, 4), (255, 0, 0)), _solid((4, 4), (0, 255, 0))]
    grid = pil_grid(images, max_horiz=2)
    arr = np.array(grid)
    assert tuple(arr[0, 0]) == (255, 0, 0)
    assert tuple(arr[0, 4]) == (0, 255, 0)


# ---------------------------------------------------------------------------
# pad_or_trim_images (extracted from AssembleImageAction.run)
# ---------------------------------------------------------------------------

def test_pad_or_trim_images_pads_underfull_grid():
    images = [_solid((10, 10))]
    result = pad_or_trim_images(images, target_count=4, image_size=(10, 10))
    assert len(result) == 4
    # the padding frames are blank white
    assert result[-1].getpixel((0, 0)) == (255, 255, 255)


def test_pad_or_trim_images_trims_overfull_grid():
    images = [_solid((10, 10)) for _ in range(5)]
    result = pad_or_trim_images(images, target_count=3, image_size=(10, 10))
    assert len(result) == 3


def test_pad_or_trim_images_exact_fit_is_unchanged():
    images = [_solid((10, 10)) for _ in range(4)]
    result = pad_or_trim_images(images, target_count=4, image_size=(10, 10))
    assert result is images
    assert len(result) == 4


def test_pad_or_trim_images_mutates_and_returns_same_list():
    images = [_solid((10, 10))]
    result = pad_or_trim_images(images, target_count=2, image_size=(10, 10))
    assert result is images


# ---------------------------------------------------------------------------
# convert_synctex_to_image_coords
# ---------------------------------------------------------------------------

@pytest.fixture
def action():
    return AssembleImageAction()


def test_convert_synctex_to_image_coords_identity_scale(action):
    # pdf and image sizes equal -> ratios are 1, so the only transform is
    # the y-axis flip (PDF origin bottom-left, image origin top-left).
    pdf_size = (100.0, 200.0)
    image_size = (100, 200)
    synctex_coords = {'x': 10, 'y': 20, 'h': 5, 'v': 15, 'W': 30, 'H': 40}

    x, y, h, v, W, H = action.convert_synctex_to_image_coords(pdf_size, image_size, synctex_coords)

    assert x == 10
    assert y == 200 - 20
    assert h == 5   # h uses y_ratio
    assert v == 15  # v uses x_ratio
    assert W == 30
    assert H == 40


def test_convert_synctex_to_image_coords_scales_with_ratio(action):
    pdf_size = (100.0, 100.0)
    image_size = (200, 50)  # 2x width, 0.5x height
    synctex_coords = {'x': 10, 'y': 10, 'h': 10, 'v': 10, 'W': 10, 'H': 10}

    x, y, h, v, W, H = action.convert_synctex_to_image_coords(pdf_size, image_size, synctex_coords)

    assert x == 20     # x * x_ratio(2)
    assert y == 50 - 5  # image_height - y * y_ratio(0.5)
    assert h == 5       # h * y_ratio(0.5)
    assert v == 20      # v * x_ratio(2)
    assert W == 20       # W * x_ratio(2)
    assert H == 5        # H * y_ratio(0.5)


# ---------------------------------------------------------------------------
# crop_box_for_page
# ---------------------------------------------------------------------------

def test_crop_box_for_page_crop_off_is_full_box_noop():
    config = Config(crop=False, cropLeft=50, cropRight=50, cropTop=50, cropBottom=50)
    box = crop_box_for_page(config, page_index=0, width=1000, height=2000)
    assert box == (0, 0, 1000, 2000)


def test_crop_box_for_page_single_page_mode_applies_same_box_to_every_page():
    config = Config(crop=True, cropTwoPage=False,
                     cropLeft=10, cropRight=20, cropTop=30, cropBottom=40,
                     cropAltLeft=999, cropAltRight=999, cropAltTop=999, cropAltBottom=999)
    even_box = crop_box_for_page(config, page_index=0, width=1000, height=2000)
    odd_box = crop_box_for_page(config, page_index=1, width=1000, height=2000)

    expected = (10, 30, 1000 - 20, 2000 - 40)
    assert even_box == expected
    assert odd_box == expected  # cropAlt* must be ignored when cropTwoPage is off


def test_crop_box_for_page_two_page_mode_even_page_uses_primary_crop():
    config = Config(crop=True, cropTwoPage=True,
                     cropLeft=10, cropRight=20, cropTop=30, cropBottom=40,
                     cropAltLeft=1, cropAltRight=2, cropAltTop=3, cropAltBottom=4)
    box = crop_box_for_page(config, page_index=0, width=1000, height=2000)
    assert box == (10, 30, 1000 - 20, 2000 - 40)


def test_crop_box_for_page_two_page_mode_odd_page_uses_alt_crop():
    config = Config(crop=True, cropTwoPage=True,
                     cropLeft=10, cropRight=20, cropTop=30, cropBottom=40,
                     cropAltLeft=1, cropAltRight=2, cropAltTop=3, cropAltBottom=4)
    box = crop_box_for_page(config, page_index=1, width=1000, height=2000)
    assert box == (1, 3, 1000 - 2, 2000 - 4)


def test_crop_box_for_page_two_page_mode_alternates_by_parity():
    config = Config(crop=True, cropTwoPage=True,
                     cropLeft=10, cropRight=20, cropTop=30, cropBottom=40,
                     cropAltLeft=1, cropAltRight=2, cropAltTop=3, cropAltBottom=4)
    even_box = crop_box_for_page(config, page_index=2, width=1000, height=2000)
    odd_box = crop_box_for_page(config, page_index=3, width=1000, height=2000)
    assert even_box == (10, 30, 1000 - 20, 2000 - 40)
    assert odd_box == (1, 3, 1000 - 2, 2000 - 4)


def test_crop_box_for_page_clamps_oversized_horizontal_insets_to_a_noop():
    # left + right >= width -> defensively skip the crop rather than
    # producing a zero/negative-size image.
    config = Config(crop=True, cropLeft=600, cropRight=600, cropTop=0, cropBottom=0)
    box = crop_box_for_page(config, page_index=0, width=1000, height=2000)
    assert box == (0, 0, 1000, 2000)


def test_crop_box_for_page_clamps_oversized_vertical_insets_to_a_noop():
    config = Config(crop=True, cropLeft=0, cropRight=0, cropTop=1500, cropBottom=1500)
    box = crop_box_for_page(config, page_index=0, width=1000, height=2000)
    assert box == (0, 0, 1000, 2000)


def test_crop_box_for_page_clamps_exact_equality_too():
    # left + right == width should also be treated as a defensive clamp
    # case, not just strictly-greater-than.
    config = Config(crop=True, cropLeft=500, cropRight=500, cropTop=0, cropBottom=0)
    box = crop_box_for_page(config, page_index=0, width=1000, height=2000)
    assert box == (0, 0, 1000, 2000)


# ---------------------------------------------------------------------------
# Overlay coordinates offset by the page's crop (see AssembleImageAction.run:
# a synctex point computed against the full/uncropped page must be shifted
# into the cropped image's local origin before it's usable as a pixel coord).
# ---------------------------------------------------------------------------

def test_overlay_coordinate_offset_by_crop(action):
    # A synctex point that lands at (100, 100) in the full-page coordinate
    # space must become (100 - cropLeft, 100 - cropTop) once that page has
    # been cropped - the crop moves the image's local origin.
    pdf_size = (100.0, 100.0)
    full_image_size = (100, 100)  # identity scale, to keep h/v == x/y-ish easy to reason about
    synctex_coords = {'x': 0, 'y': 100, 'h': 100, 'v': 100, 'W': 0, 'H': 0}

    _, _, h, v, _, _ = action.convert_synctex_to_image_coords(pdf_size, full_image_size, synctex_coords)
    assert (h, v) == (100, 100)

    crop_left, crop_top = 15, 25
    h -= crop_left
    v -= crop_top

    assert (h, v) == (100 - 15, 100 - 25)
