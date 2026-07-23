"""Regression tests for tex_timelapse.core.actions.pdf_to_image: snapshot.pages
must contain bare basenames only, never absolute/workdir-rooted paths (see
commit d3d252d - the old `glob(f'{snapshot_img_dir}/*.jpg')` stored full
paths into the workdir, which compiler.py then deletes after every run,
leaving snapshots.yaml with dangling references).

pypdfium2 itself is faked out (see FakePdfDocument below) - no real PDF
bytes or actual rasterisation involved, so this needs neither LaTeX nor a
real PDF file. The real code path (including the PDFIUM_LOCK acquisition)
still runs, just against a fake pdfium.PdfDocument.
"""

import os
from pathlib import Path

import pytest
from PIL import Image

import tex_timelapse.core.actions.pdf_to_image as pdf_to_image_module
from tex_timelapse.core.actions.pdf_to_image import PdfToImageAction
from tex_timelapse.core.snapshot import Snapshot, SnapshotStatus


class FakeBitmap:
    def __init__(self, image):
        self._image = image
        self.closed = False

    def to_pil(self):
        return self._image

    def close(self):
        self.closed = True


class FakePage:
    def __init__(self, image):
        self._image = image
        self.closed = False

    def render(self, scale=1.0):
        return FakeBitmap(self._image)

    def get_size(self):
        return self._image.size

    def close(self):
        self.closed = True


class FakePdfDocument:
    """Stands in for pypdfium2.PdfDocument: a fixed page count, each page a
    small solid-colour image - no real PDF bytes are parsed."""
    def __init__(self, path, page_count=2):
        self.path = path
        self._page_count = page_count
        self.closed = False

    def __len__(self):
        return self._page_count

    def get_page(self, i):
        return FakePage(Image.new('RGB', (20, 30), color='white'))

    def close(self):
        self.closed = True


@pytest.fixture
def fake_pdfium(monkeypatch):
    monkeypatch.setattr(pdf_to_image_module.pdfium, 'PdfDocument', lambda path: FakePdfDocument(path))


class FakeProject:
    def __init__(self, project_folder: str):
        self.projectFolder = project_folder


def test_pages_stores_bare_basenames_not_absolute_paths(tmp_path, fake_pdfium):
    workdir = tmp_path / 'workdir'
    workdir.mkdir()

    snapshot = Snapshot('cafef00d', 1700000000, 0)
    snapshot.setWorkDir(str(workdir))
    snapshot.main_tex_file = './main.tex'

    action = PdfToImageAction()
    action.init(FakeProject(str(tmp_path / 'project')))
    result = action.run(snapshot)

    assert result == SnapshotStatus.COMPLETED
    assert len(snapshot.pages) == 2

    for page in snapshot.pages:
        # the regression: no path separators, no workdir prefix, and
        # basename(page) == page (i.e. it already is just a basename)
        assert '/' not in page
        assert os.path.basename(page) == page
        assert not os.path.isabs(page)
        assert str(workdir) not in page


def test_pages_are_sorted_and_zero_padded_to_page_count_width(tmp_path, monkeypatch):
    # 10 pages -> zero-padding must be 2 digits wide so lexicographic sort
    # matches numeric order (page-01.jpg < page-02.jpg < ... < page-10.jpg)
    monkeypatch.setattr(
        pdf_to_image_module.pdfium, 'PdfDocument',
        lambda path: FakePdfDocument(path, page_count=10),
    )

    workdir = tmp_path / 'workdir'
    workdir.mkdir()
    snapshot = Snapshot('cafef00d', 1700000000, 0)
    snapshot.setWorkDir(str(workdir))
    snapshot.main_tex_file = './main.tex'

    action = PdfToImageAction()
    action.init(FakeProject(str(tmp_path / 'project')))
    action.run(snapshot)

    assert snapshot.pages == sorted(snapshot.pages)
    assert snapshot.pages[0] == 'page-01.jpg'
    assert snapshot.pages[-1] == 'page-10.jpg'


def test_run_writes_full_size_and_thumbnail_images_to_disk(tmp_path, fake_pdfium):
    workdir = tmp_path / 'workdir'
    workdir.mkdir()
    project_folder = tmp_path / 'project'

    snapshot = Snapshot('cafef00d', 1700000000, 0)
    snapshot.setWorkDir(str(workdir))
    snapshot.main_tex_file = './main.tex'

    action = PdfToImageAction()
    action.init(FakeProject(str(project_folder)))
    action.run(snapshot)

    for page in snapshot.pages:
        assert (workdir / 'images' / page).exists()
        assert (project_folder / 'thumbnails' / 'cafef00d' / page).exists()


def test_reset_clears_pages_and_removes_thumbnail_dir(tmp_path, fake_pdfium):
    workdir = tmp_path / 'workdir'
    workdir.mkdir()
    project_folder = tmp_path / 'project'

    snapshot = Snapshot('cafef00d', 1700000000, 0)
    snapshot.setWorkDir(str(workdir))
    snapshot.main_tex_file = './main.tex'

    action = PdfToImageAction()
    action.init(FakeProject(str(project_folder)))
    action.run(snapshot)

    thumb_dir = project_folder / 'thumbnails' / 'cafef00d'
    assert thumb_dir.exists()

    action.reset(snapshot)

    assert snapshot.pages == []
    assert not thumb_dir.exists()
