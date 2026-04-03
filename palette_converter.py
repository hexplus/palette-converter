"""
Palette Format Converter
========================
Converts between palette formats commonly used in pixel art tools.

Source formats (read):
  .pal (JASC)    - JASC-PAL text format
  .ase           - Adobe Swatch Exchange
  .txt           - Paint.net palette
  .gpl           - GIMP palette
  .hex           - Hex color list
  .png           - Palette swatch image (reads unique colors)

Target formats (write):
  .pal (RIFF)    - Microsoft RIFF PAL (Palette *.pal)
  .act           - Adobe Color Table (*.act)
  .dpf           - D-Pixed Palette (*.dpf)
  .dib / .bmp    - Bitmap palette swatch (*.dib, *.bmp)
  .ico           - Icon palette swatch (*.ico)
  .cur           - Cursor palette swatch (*.cur)
  .gif           - GIF palette swatch (*.gif)
  .gal           - Gale palette (*.gal)
  .png           - PNG palette swatch (*.png)
  .tga           - TGA palette swatch (*.tga)

Usage:
  python palette_converter.py input.gpl output.act
  python palette_converter.py input.hex output.pal
  python palette_converter.py input.ase output.png
  python palette_converter.py input.gpl --all    (exports to all formats)
"""

import struct
import sys
import os

# =============================================
# READERS (source formats)
# =============================================

def read_jasc_pal(filepath):
    """Read JASC-PAL format (used by Paint Shop Pro, GraphicsGale, etc.)"""
    colors = []
    with open(filepath, "r") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    if lines[0] != "JASC-PAL":
        raise ValueError("Not a valid JASC-PAL file")
    # lines[1] = version (0100), lines[2] = color count
    count = int(lines[2])
    for i in range(3, 3 + count):
        parts = lines[i].split()
        r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
        colors.append((r, g, b))
    return colors


def read_ase(filepath):
    """Read Adobe Swatch Exchange (.ase) format."""
    colors = []
    with open(filepath, "rb") as f:
        sig = f.read(4)
        if sig != b"ASEF":
            raise ValueError("Not a valid ASE file")
        _version = struct.unpack(">HH", f.read(4))
        num_blocks = struct.unpack(">I", f.read(4))[0]

        for _ in range(num_blocks):
            block_type = struct.unpack(">H", f.read(2))[0]
            block_len = struct.unpack(">I", f.read(4))[0]
            block_data = f.read(block_len)

            if block_type == 0x0001:  # Color entry
                # Name: uint16 length + UTF-16BE string
                name_len = struct.unpack(">H", block_data[0:2])[0]
                offset = 2 + name_len * 2
                color_model = block_data[offset:offset + 4].decode("ascii", errors="ignore")
                offset += 4

                if color_model.startswith("RGB"):
                    rf = struct.unpack(">f", block_data[offset:offset + 4])[0]
                    gf = struct.unpack(">f", block_data[offset + 4:offset + 8])[0]
                    bf = struct.unpack(">f", block_data[offset + 8:offset + 12])[0]
                    colors.append((
                        max(0, min(255, int(rf * 255))),
                        max(0, min(255, int(gf * 255))),
                        max(0, min(255, int(bf * 255)))
                    ))
    return colors


def read_paintnet_txt(filepath):
    """Read Paint.net palette .txt format."""
    colors = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            # Format: AARRGGBB or RRGGBB (hex)
            h = line.lstrip("#").replace("0x", "").replace("0X", "")
            if len(h) == 8:  # AARRGGBB
                r = int(h[2:4], 16)
                g = int(h[4:6], 16)
                b = int(h[6:8], 16)
            elif len(h) == 6:  # RRGGBB
                r = int(h[0:2], 16)
                g = int(h[2:4], 16)
                b = int(h[4:6], 16)
            else:
                continue
            colors.append((r, g, b))
    return colors


def read_gimp_gpl(filepath):
    """Read GIMP .gpl palette format."""
    colors = []
    with open(filepath, "r") as f:
        header_found = False
        for line in f:
            line = line.strip()
            if not header_found:
                if line == "GIMP Palette":
                    header_found = True
                continue
            if not line or line.startswith("#") or line.startswith("Name:") or line.startswith("Columns:"):
                continue
            parts = line.split()
            if len(parts) >= 3:
                try:
                    r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                    colors.append((r, g, b))
                except ValueError:
                    continue
    return colors


def read_hex_file(filepath):
    """Read .hex color list (one hex color per line)."""
    colors = []
    with open(filepath, "r") as f:
        for line in f:
            h = line.strip().lstrip("#")
            if len(h) == 6:
                try:
                    r = int(h[0:2], 16)
                    g = int(h[2:4], 16)
                    b = int(h[4:6], 16)
                    colors.append((r, g, b))
                except ValueError:
                    continue
    return colors


def read_png_palette(filepath):
    """Read colors from a PNG image (unique colors in order of appearance)."""
    from PIL import Image
    img = Image.open(filepath).convert("RGB")
    seen = set()
    colors = []
    for y in range(img.height):
        for x in range(img.width):
            c = img.getpixel((x, y))
            if c not in seen:
                seen.add(c)
                colors.append(c)
    return colors


# =============================================
# WRITERS (target formats)
# =============================================

def write_jasc_pal(colors, filepath):
    """Write JASC-PAL format (GraphicsGale, Paint Shop Pro, etc.)
    Always writes 256 entries (required by GraphicsGale)."""
    padded = list(colors) + [(0, 0, 0)] * (256 - len(colors))
    with open(filepath, "w") as f:
        f.write("JASC-PAL\r\n")
        f.write("0100\r\n")
        f.write("256\r\n")
        for r, g, b in padded:
            f.write(f"{r} {g} {b}\r\n")


def write_act(colors, filepath):
    """Write Adobe Color Table (.act) - 768 bytes (256 x RGB)."""
    data = bytearray(768)
    for i, (r, g, b) in enumerate(colors[:256]):
        data[i * 3] = r
        data[i * 3 + 1] = g
        data[i * 3 + 2] = b
    with open(filepath, "wb") as f:
        f.write(data)


def write_dpf(colors, filepath):
    """Write D-Pixed Palette (.dpf) format."""
    with open(filepath, "w") as f:
        f.write("DPixed Palette File\r\n")
        f.write(f"{len(colors)}\r\n")
        for r, g, b in colors:
            f.write(f"{r} {g} {b}\r\n")


def _make_swatch_image(colors, cell_size=16):
    """Create a swatch grid image from colors. Returns (pixels, width, height)."""
    n = len(colors)
    cols = min(n, 16)
    rows = (n + cols - 1) // cols
    w = cols * cell_size
    h = rows * cell_size

    pixels = []
    for y in range(h):
        row = []
        for x in range(w):
            ci = (y // cell_size) * cols + (x // cell_size)
            if ci < n:
                row.append(colors[ci])
            else:
                row.append((0, 0, 0))
        pixels.append(row)
    return pixels, w, h


def write_bmp(colors, filepath):
    """Write BMP palette swatch image."""
    from PIL import Image
    px, w, h = _make_swatch_image(colors)
    img = Image.new("RGB", (w, h))
    for y in range(h):
        for x in range(w):
            img.putpixel((x, y), px[y][x])
    img.save(filepath, "BMP")


def write_dib(colors, filepath):
    """Write DIB (headerless BMP) palette swatch."""
    # DIB is essentially BMP without the file header (first 14 bytes)
    from PIL import Image
    import io
    px, w, h = _make_swatch_image(colors)
    img = Image.new("RGB", (w, h))
    for y in range(h):
        for x in range(w):
            img.putpixel((x, y), px[y][x])
    buf = io.BytesIO()
    img.save(buf, "BMP")
    bmp_data = buf.getvalue()
    with open(filepath, "wb") as f:
        f.write(bmp_data[14:])  # Skip BITMAPFILEHEADER


def write_ico(colors, filepath):
    """Write ICO palette swatch (16x16 or smaller)."""
    from PIL import Image
    n = min(len(colors), 256)
    side = 16
    img = Image.new("RGB", (side, side), (0, 0, 0))
    cols = min(n, side)
    for i in range(n):
        x = i % cols
        y = i // cols
        if y < side:
            img.putpixel((x, y), colors[i])
    img.save(filepath, "ICO", sizes=[(side, side)])


def write_cur(colors, filepath):
    """Write CUR cursor file with palette swatch."""
    from PIL import Image
    import io
    n = min(len(colors), 256)
    side = 16
    img = Image.new("RGB", (side, side), (0, 0, 0))
    cols = min(n, side)
    for i in range(n):
        x = i % cols
        y = i // cols
        if y < side:
            img.putpixel((x, y), colors[i])
    # Build BMP image data (no file header, just DIB)
    buf = io.BytesIO()
    img.save(buf, "BMP")
    bmp_data = buf.getvalue()
    # BMP file header is 14 bytes; skip it to get DIB header + pixel data
    dib_data = bytearray(bmp_data[14:])
    # CUR requires double-height in DIB header (XOR mask + AND mask)
    struct.pack_into("<i", dib_data, 4, side * 2)
    # AND mask: 1-bit transparency mask, all zeros (fully opaque)
    row_bytes = ((side + 31) // 32) * 4  # rows padded to 4-byte boundary
    and_mask = b'\x00' * (row_bytes * side)
    image_data = bytes(dib_data) + and_mask
    # CUR header: reserved(2) + type(2=CUR) + count(2)
    header = struct.pack("<HHH", 0, 2, 1)
    # Directory entry: width, height, colorcount, reserved,
    #                  hotspot_x(2), hotspot_y(2), size(4), offset(4)
    dir_entry = struct.pack("<BBBBHHII",
                            side, side, 0, 0,
                            0, 0,  # hotspot x, y
                            len(image_data),
                            6 + 16)  # offset = header(6) + dir_entry(16)
    with open(filepath, "wb") as f:
        f.write(header)
        f.write(dir_entry)
        f.write(image_data)


def write_gif(colors, filepath):
    """Write GIF palette swatch."""
    from PIL import Image
    px, w, h = _make_swatch_image(colors)
    img = Image.new("RGB", (w, h))
    for y in range(h):
        for x in range(w):
            img.putpixel((x, y), px[y][x])
    img = img.quantize(colors=len(colors))
    img.save(filepath, "GIF")


def write_gal(colors, filepath):
    """Write GraphicsGale .gal palette swatch (minimal single-frame)."""
    from PIL import Image
    import io
    # GraphicsGale .gal is a proprietary format.
    # Simplest approach: write as BMP with .gal extension
    # GraphicsGale can open BMP files renamed to .gal
    px, w, h = _make_swatch_image(colors)
    img = Image.new("P", (w, h))
    # Build indexed palette
    pal_flat = []
    for r, g, b in colors:
        pal_flat.extend([r, g, b])
    while len(pal_flat) < 768:
        pal_flat.extend([0, 0, 0])
    img.putpalette(pal_flat)
    # Map pixels to palette indices
    color_to_idx = {c: i for i, c in enumerate(colors)}
    for y in range(h):
        for x in range(w):
            c = px[y][x]
            img.putpixel((x, y), color_to_idx.get(c, 0))
    img.save(filepath, "BMP")


def write_png(colors, filepath):
    """Write PNG palette swatch."""
    from PIL import Image
    px, w, h = _make_swatch_image(colors)
    img = Image.new("RGB", (w, h))
    for y in range(h):
        for x in range(w):
            img.putpixel((x, y), px[y][x])
    img.save(filepath, "PNG")


def write_tga(colors, filepath):
    """Write TGA palette swatch (uncompressed RGB)."""
    px, w, h = _make_swatch_image(colors)
    with open(filepath, "wb") as f:
        # TGA header (18 bytes)
        f.write(struct.pack("<BBBHHBHHHHBB",
            0,    # ID length
            0,    # Color map type
            2,    # Image type (uncompressed RGB)
            0, 0, # Color map spec
            0,    # Color map entry size
            0, 0, # X origin
            w, h, # Width, height
            24,   # Bits per pixel
            0x20  # Image descriptor (top-left origin)
        ))
        # Pixel data (BGR)
        for y in range(h):
            for x in range(w):
                r, g, b = px[y][x]
                f.write(bytes([b, g, r]))


# =============================================
# Format registry
# =============================================

READERS = {
    ".pal": read_jasc_pal,
    ".ase": read_ase,
    ".txt": read_paintnet_txt,
    ".gpl": read_gimp_gpl,
    ".hex": read_hex_file,
    ".png": read_png_palette,
}

WRITERS = {
    ".pal": ("Palette (JASC-PAL)", write_jasc_pal),
    ".act": ("Adobe Color Table", write_act),
    ".dpf": ("D-Pixed Palette", write_dpf),
    ".dib": ("Device Independent Bitmap", write_dib),
    ".bmp": ("Bitmap", write_bmp),
    ".ico": ("Icon", write_ico),
    ".cur": ("Cursor", write_cur),
    ".gif": ("GIF", write_gif),
    ".gal": ("Gale", write_gal),
    ".png": ("PNG", write_png),
    ".tga": ("TGA", write_tga),
}


def detect_reader(filepath):
    """Detect the right reader based on extension and content."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in READERS:
        return READERS[ext]
    raise ValueError(f"Unsupported input format: {ext}\nSupported: {', '.join(READERS.keys())}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("Supported input formats:", ", ".join(READERS.keys()))
        print("Supported output formats:", ", ".join(WRITERS.keys()))
        sys.exit(1)

    input_path = sys.argv[1]
    output_arg = sys.argv[2]

    TARGET_SIZE = 16  # SNES 4bpp = 16 colors per palette

    # Read input palette
    reader = detect_reader(input_path)
    colors = reader(input_path)
    print(f"Read {len(colors)} colors from {input_path}")

    # Enforce 16 colors
    if len(colors) > TARGET_SIZE:
        print(f"  WARNING: Truncating from {len(colors)} to {TARGET_SIZE} colors")
        colors = colors[:TARGET_SIZE]
    elif len(colors) < TARGET_SIZE:
        pad = TARGET_SIZE - len(colors)
        print(f"  Padding {pad} empty slot(s) with black")
        colors += [(0, 0, 0)] * pad

    print(f"Palette ({TARGET_SIZE} colors):")
    for i, (r, g, b) in enumerate(colors):
        print(f"  {i:2d}: RGB({r:3d},{g:3d},{b:3d})  #{r:02X}{g:02X}{b:02X}")

    if output_arg == "--all":
        # Export to all formats
        base = os.path.splitext(input_path)[0]
        for ext, (desc, writer) in WRITERS.items():
            out = base + ext
            try:
                writer(colors, out)
                print(f"  -> {out} ({desc})")
            except Exception as e:
                print(f"  !! {out} FAILED: {e}")
    else:
        ext = os.path.splitext(output_arg)[1].lower()
        if ext not in WRITERS:
            print(f"Unsupported output format: {ext}")
            print(f"Supported: {', '.join(WRITERS.keys())}")
            sys.exit(1)
        desc, writer = WRITERS[ext]
        writer(colors, output_arg)
        print(f"Wrote {output_arg} ({desc})")


if __name__ == "__main__":
    main()
