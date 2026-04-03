# palette-converter

A small command-line palette format converter for pixel art palettes.

## Overview

`palette_converter.py` converts between common palette formats (input) and exports into several output formats including swatch images.

Supported input formats:
- `.pal` (JASC-PAL)
- `.ase` (Adobe Swatch Exchange)
- `.txt` (Paint.net palette)
- `.gpl` (GIMP palette)
- `.hex` (one hex color per line)
- `.png` (reads unique colors from an image)

Supported output formats:
- `.pal` (JASC RIFF PAL)
- `.act` (Adobe Color Table)
- `.dpf` (D-Pixed Palette)
- `.dib` (Device Independent Bitmap)
- `.bmp` (Bitmap swatch image)
- `.ico` (Icon swatch)
- `.cur` (Cursor swatch)
- `.gif` (GIF swatch)
- `.gal` (GraphicsGale)
- `.png` (PNG swatch)
- `.tga` (TGA swatch)

## Requirements

- Python 3.7+
- `Pillow` (for image-based input/output formats)

Install with:

```bash
pip install Pillow
```

## Usage

```bash
python palette_converter.py input.gpl output.act
python palette_converter.py input.hex output.pal
python palette_converter.py input.ase output.png
python palette_converter.py input.gpl --all
```

- `input` can be any supported source format.
- `output` can be any supported target format.
- `--all` (if available in script) triggers export to all supported outputs.

## Notes

- For `.pal` input, the script reads JASC-PAL text format.
- For `.png` input, it extracts unique colors from the source image in order of appearance.
- For `.pal` output, the generated palette is padded to 256 entries (per format requirements).
