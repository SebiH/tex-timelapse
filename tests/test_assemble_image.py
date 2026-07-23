"""Tests for tex_timelapse.actions.assemble_image's pure geometry helpers:
pil_grid, pad_or_trim_images, and convert_synctex_to_image_coords."""

import numpy as np
import pytest
from PIL import Image

from tex_timelapse.actions.assemble_image import (
    AssembleImageAction,
    pad_or_trim_images,
    pil_grid,
)


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
