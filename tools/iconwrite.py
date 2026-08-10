"""Pure-stdlib PNG and multi-size ICO writers (32-bit with alpha)."""

import struct
import zlib


def write_png(path, size, rgba):
    """rgba is a top-down RGBA bytearray of length size*size*4."""

    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    stride = size * 4
    raw = bytearray()
    for y in range(size):
        raw.append(0)
        raw.extend(rgba[y * stride:(y + 1) * stride])
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(raw), 9)
    with open(path, "wb") as f:
        f.write(signature)
        f.write(chunk(b"IHDR", ihdr))
        f.write(chunk(b"IDAT", idat))
        f.write(chunk(b"IEND", b""))


def _bmp_dib(size, rgba):
    """Encode an image as the 32-bit BMP DIB used inside .ico files."""
    header = struct.pack(
        "<IiiHHIIiiII",
        40,
        size,
        size * 2,
        1,
        32,
        0,
        size * size * 4,
        0,
        0,
        0,
        0,
    )
    pixels = bytearray()
    stride = size * 4
    for y in range(size - 1, -1, -1):
        row = rgba[y * stride:(y + 1) * stride]
        for x in range(size):
            base = x * 4
            pixels.append(row[base + 2])  # B
            pixels.append(row[base + 1])  # G
            pixels.append(row[base])      # R
            pixels.append(row[base + 3])  # A
    and_stride = ((size + 31) // 32) * 4
    mask = bytearray(and_stride * size)
    return header + bytes(pixels) + bytes(mask)


def write_ico(path, images):
    """images: list of (size, top-down RGBA bytearray)."""
    blobs = [(size, _bmp_dib(size, rgba)) for size, rgba in images]
    offset = 6 + 16 * len(blobs)
    header = struct.pack("<HHH", 0, 1, len(blobs))
    out = bytearray(header)
    for size, blob in blobs:
        dim = 0 if size >= 256 else size
        out += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    for _, blob in blobs:
        out += blob
    with open(path, "wb") as f:
        f.write(out)
