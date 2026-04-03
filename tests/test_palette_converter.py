import os
from pathlib import Path
import sys

import pytest
from PIL import Image

# Add repository root to path to import script module directly
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import palette_converter as pc

SAMPLE_COLORS = [
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 255, 0),
    (255, 0, 255),
    (0, 255, 255),
    (128, 128, 128),
    (0, 0, 0),
    (255, 255, 255),
    (42, 99, 150)
]


def test_read_write_textual_pal(tmp_path):
    pal_path = tmp_path / "sample.pal"
    pc.write_jasc_pal(SAMPLE_COLORS, pal_path)
    assert pal_path.exists()

    read_colors = pc.read_jasc_pal(pal_path)
    assert read_colors[: len(SAMPLE_COLORS)] == SAMPLE_COLORS


def test_read_write_gpl(tmp_path):
    gpl_path = tmp_path / "sample.gpl"
    with open(gpl_path, "w") as f:
        f.write("GIMP Palette\n")
        f.write("# Sample\n")
        for r, g, b in SAMPLE_COLORS:
            f.write(f"{r} {g} {b} color\n")

    read_colors = pc.read_gimp_gpl(gpl_path)
    assert read_colors == SAMPLE_COLORS


def test_read_write_txt(tmp_path):
    txt_path = tmp_path / "sample.txt"
    with open(txt_path, "w") as f:
        for r, g, b in SAMPLE_COLORS:
            f.write(f"#{r:02X}{g:02X}{b:02X}\n")

    read_colors = pc.read_paintnet_txt(txt_path)
    assert read_colors == SAMPLE_COLORS


def test_read_write_hex(tmp_path):
    hex_path = tmp_path / "sample.hex"
    with open(hex_path, "w") as f:
        for r, g, b in SAMPLE_COLORS:
            f.write(f"{r:02X}{g:02X}{b:02X}\n")

    read_colors = pc.read_hex_file(hex_path)
    assert read_colors == SAMPLE_COLORS


def test_read_write_png_palette(tmp_path):
    png_in = tmp_path / "sample_in.png"
    img = Image.new("RGB", (len(SAMPLE_COLORS), 1))
    for x, c in enumerate(SAMPLE_COLORS):
        img.putpixel((x, 0), c)
    img.save(png_in)

    read_colors = pc.read_png_palette(png_in)
    assert read_colors == SAMPLE_COLORS


@pytest.mark.parametrize("ext", list(pc.WRITERS.keys()))
def test_all_writers_create_file(tmp_path, ext):
    out_path = tmp_path / f"output{ext}"
    writer = pc.WRITERS[ext][1]
    writer(SAMPLE_COLORS, out_path)
    assert out_path.exists(), f"{ext} writer did not create output" 

    # For image outputs, verify shape and first colors.
    if ext in [".bmp", ".png", ".ico", ".cur", ".gif", ".gal", ".dib"]:
        im = Image.open(out_path)
        assert im.width > 0 and im.height > 0

        if ext in [".bmp", ".png", ".gif", ".gal"]:
            # top-left pixel from swatch should be first color
            rgb_im = im.convert("RGB")
            assert rgb_im.getpixel((0, 0))[:3] == SAMPLE_COLORS[0]
