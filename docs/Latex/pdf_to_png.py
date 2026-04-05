"""
Crop a PDF to its content bounding box and render it as a PNG at a given DPI.
Uses only Ghostscript (gs) and the Python standard library — no extra packages.

Usage: python3 pdf_to_png.py <input.pdf> <output.png> [dpi]

Strategy:
  1. Ask gs for the exact content HiResBoundingBox (in PDF points).
  2. Ask gs for the page MediaBox size (in PDF points).
  3. Render the full page to an uncompressed PPM temp file.
  4. Compute the crop rectangle in pixels (accounting for y-axis flip between
     PDF and raster space).
  5. Crop the PPM and write a proper PNG — all in pure Python.
"""

import os
import re
import struct
import subprocess
import sys
import tempfile
import zlib


# ---------------------------------------------------------------------------
# Ghostscript helpers
# ---------------------------------------------------------------------------

def get_bbox(pdf_path: str) -> tuple[float, float, float, float]:
    """Return (x0, y0, x1, y1) in PDF points of the content bounding box."""
    result = subprocess.run(
        ["gs", "-dNOPAUSE", "-dBATCH", "-sDEVICE=bbox", pdf_path],
        capture_output=True, text=True,
    )
    m = re.search(
        r"%%HiResBoundingBox:\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)",
        result.stderr,
    )
    if not m:
        raise RuntimeError(f"Could not parse bounding box:\n{result.stderr}")
    return float(m[1]), float(m[2]), float(m[3]), float(m[4])




def render_ppm(pdf_path: str, ppm_path: str, dpi: int) -> None:
    """Render the full first page to an uncompressed RGB PPM file."""
    subprocess.run(
        ["gs", "-dNOPAUSE", "-dBATCH",
         "-sDEVICE=ppmraw", f"-r{dpi}",
         f"-sOutputFile={ppm_path}",
         pdf_path],
        check=True, capture_output=True,
    )


# ---------------------------------------------------------------------------
# PPM reader
# ---------------------------------------------------------------------------

def read_ppm(path: str) -> tuple[int, int, bytes]:
    """Return (width, height, raw_rgb_bytes) from a binary PPM (P6) file."""
    with open(path, "rb") as f:
        raw = f.read()

    pos = 0

    def next_token() -> bytes:
        nonlocal pos
        # Skip whitespace and comments
        while pos < len(raw) and (raw[pos:pos+1] in (b' ', b'\t', b'\n', b'\r')
                                   or raw[pos:pos+1] == b'#'):
            if raw[pos:pos+1] == b'#':
                while pos < len(raw) and raw[pos:pos+1] != b'\n':
                    pos += 1
            pos += 1
        start = pos
        while pos < len(raw) and raw[pos:pos+1] not in (b' ', b'\t', b'\n', b'\r'):
            pos += 1
        return raw[start:pos]

    magic = next_token()
    assert magic == b"P6", f"Expected P6 PPM, got {magic}"
    width  = int(next_token())
    height = int(next_token())
    maxval = int(next_token())
    assert maxval == 255
    pos += 1  # skip the single whitespace byte after maxval
    return width, height, raw[pos:]


# ---------------------------------------------------------------------------
# PNG writer (pure stdlib)
# ---------------------------------------------------------------------------

def _chunk(tag: bytes, data: bytes) -> bytes:
    body = tag + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def write_png(path: str, width: int, height: int, raw_rgb: bytes) -> None:
    """Write a 24-bit RGB PNG from raw row-major RGB bytes (no filter bytes)."""
    row_size = width * 3
    # Prepend filter-type 0 (None) before each row
    filtered = bytearray()
    for y in range(height):
        filtered.append(0)
        filtered += raw_rgb[y * row_size: (y + 1) * row_size]

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(bytes(filtered), 6)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(_chunk(b"IHDR", ihdr))
        f.write(_chunk(b"IDAT", idat))
        f.write(_chunk(b"IEND", b""))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def render(pdf_path: str, png_path: str, dpi: int) -> None:
    # 1. Content bounding box in PDF points
    bx0, by0, bx1, by1 = get_bbox(pdf_path)

    # 2. Render full page to temp PPM
    tmp_ppm = tempfile.mktemp(suffix=".ppm")
    try:
        render_ppm(pdf_path, tmp_ppm, dpi)
        img_w, img_h, ppm_raw = read_ppm(tmp_ppm)
    finally:
        if os.path.exists(tmp_ppm):
            os.remove(tmp_ppm)

    # 3. Convert bbox from PDF points to pixel coordinates.
    #    The scale (px/pt) is dpi/72. PDF y=0 is at the bottom of the page;
    #    PNG y=0 is at the top, so y-coordinates are mirrored around img_h.
    scale = dpi / 72.0

    px0 = max(0,      int(bx0 * scale))
    px1 = min(img_w,  int(bx1 * scale) + 1)
    py0 = max(0,      img_h - int(by1 * scale) - 1)   # PDF top → PNG top
    py1 = min(img_h,  img_h - int(by0 * scale) + 1)

    crop_w = px1 - px0
    crop_h = py1 - py0
    row_size = img_w * 3

    # 5. Crop and write PNG
    cropped = bytearray()
    for y in range(py0, py1):
        start = y * row_size + px0 * 3
        cropped += ppm_raw[start: start + crop_w * 3]

    write_png(png_path, crop_w, crop_h, bytes(cropped))
    print(f"Written {png_path}: {crop_w}×{crop_h} px at {dpi} DPI")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    render(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 600)
