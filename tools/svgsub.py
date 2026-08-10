"""Minimal pure-stdlib SVG subset rasterizer used by make_icon.py.

Supports: path (M/L/H/V/C/S/Z), rect (rounded), circle, group attribute
inheritance, solid fills and round-capped/round-joined strokes.
"""

import math
import re

SVG_VIEW = 580.0
SUPERSAMPLE = 4
MIN_STROKE_PX = 1.0

_TOKEN_RE = re.compile(
    r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"
)


def parse_color(text):
    if text is None:
        return None
    s = text.strip()
    if s == "none":
        return None
    if s.startswith("#"):
        h = s[1:]
        if len(h) == 3:
            return (int(h[0] * 2, 16), int(h[1] * 2, 16), int(h[2] * 2, 16))
        if len(h) == 6:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        if len(h) == 8:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    if s == "black":
        return (0, 0, 0)
    if s == "white":
        return (255, 255, 255)
    return (0, 0, 0)


class Shape:
    __slots__ = ("polylines", "closed", "stroke_color", "stroke_width", "fill_color")

    def __init__(self):
        self.polylines = []
        self.closed = []
        self.stroke_color = None
        self.stroke_width = 0.0
        self.fill_color = None


def _tess_cubic(p0, p1, p2, p3, flat, out):
    dx, dy = p3[0] - p0[0], p3[1] - p0[1]
    length2 = dx * dx + dy * dy

    def dev(px, py):
        if length2 == 0.0:
            return math.hypot(px - p0[0], py - p0[1])
        t = max(0.0, min(1.0, ((px - p0[0]) * dx + (py - p0[1]) * dy) / length2))
        return math.hypot(px - (p0[0] + t * dx), py - (p0[1] + t * dy))

    if dev(p1[0], p1[1]) <= flat and dev(p2[0], p2[1]) <= flat:
        out.append(p3)
        return
    p01 = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
    p12 = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
    p23 = ((p2[0] + p3[0]) / 2, (p2[1] + p3[1]) / 2)
    p012 = ((p01[0] + p12[0]) / 2, (p01[1] + p12[1]) / 2)
    p123 = ((p12[0] + p23[0]) / 2, (p12[1] + p23[1]) / 2)
    p0123 = ((p012[0] + p123[0]) / 2, (p012[1] + p123[1]) / 2)
    _tess_cubic(p0, p01, p012, p0123, flat, out)
    _tess_cubic(p0123, p123, p23, p3, flat, out)


def parse_path(d):
    tokens = _TOKEN_RE.findall(d)
    subpaths = []
    closed = []
    cur = (0.0, 0.0)
    cur_poly = None
    prev_c2 = None
    last_cmd = None
    i, n = 0, len(tokens)

    def flush():
        nonlocal cur_poly
        if cur_poly is not None and cur_poly:
            subpaths.append(cur_poly)
            closed.append(False)
            cur_poly = None

    def start_at(x, y):
        nonlocal cur_poly
        flush()
        cur_poly = [(x, y)]

    while i < n:
        tok = tokens[i]
        if tok.isalpha():
            cmd = tok
            i += 1
        else:
            if last_cmd is None:
                raise ValueError("Path data must start with a command")
            cmd = last_cmd

        if cmd in "zZ":
            if cur_poly is not None and cur_poly:
                cur_poly.append(cur_poly[0])
                subpaths.append(cur_poly)
                closed.append(True)
                cur_poly = None
            prev_c2 = None
            continue

        if cmd in "Mm":
            if i + 2 > n:
                break
            x, y = float(tokens[i]), float(tokens[i + 1])
            i += 2
            if cmd == "m":
                x += cur[0]
                y += cur[1]
            start_at(x, y)
            cur = (x, y)
            last_cmd = "L" if cmd == "M" else "l"
            prev_c2 = None
            continue

        if cmd in "Ll":
            if cur_poly is None:
                cur_poly = []
            while i < n and not tokens[i].isalpha():
                if i + 2 > n:
                    i = n
                    break
                x, y = float(tokens[i]), float(tokens[i + 1])
                i += 2
                if cmd == "l":
                    x += cur[0]
                    y += cur[1]
                cur_poly.append((x, y))
                cur = (x, y)
            last_cmd = cmd
            prev_c2 = None
            continue

        if cmd in "HhVv":
            if cur_poly is None:
                cur_poly = []
            while i < n and not tokens[i].isalpha():
                v = float(tokens[i])
                i += 1
                if cmd in "Hh":
                    x = v if cmd == "H" else cur[0] + v
                    y = cur[1]
                else:
                    x = cur[0]
                    y = v if cmd == "V" else cur[1] + v
                cur_poly.append((x, y))
                cur = (x, y)
            last_cmd = cmd
            prev_c2 = None
            continue

        if cmd in "Cc":
            if cur_poly is None:
                cur_poly = []
            while i < n and not tokens[i].isalpha():
                if i + 6 > n:
                    i = n
                    break
                args = [float(tokens[i + j]) for j in range(6)]
                i += 6
                c1 = (args[0], args[1])
                c2 = (args[2], args[3])
                end = (args[4], args[5])
                if cmd == "c":
                    c1 = (cur[0] + c1[0], cur[1] + c1[1])
                    c2 = (cur[0] + c2[0], cur[1] + c2[1])
                    end = (cur[0] + end[0], cur[1] + end[1])
                _tess_cubic(cur, c1, c2, end, 0.25, cur_poly)
                prev_c2 = c2
                cur = end
            last_cmd = cmd
            continue

        if cmd in "Ss":
            if cur_poly is None:
                cur_poly = []
            while i < n and not tokens[i].isalpha():
                if i + 4 > n:
                    i = n
                    break
                args = [float(tokens[i + j]) for j in range(4)]
                i += 4
                c2 = (args[0], args[1])
                end = (args[2], args[3])
                if cmd == "s":
                    c2 = (cur[0] + c2[0], cur[1] + c2[1])
                    end = (cur[0] + end[0], cur[1] + end[1])
                if last_cmd in ("C", "c", "S", "s") and prev_c2 is not None:
                    c1 = (2 * cur[0] - prev_c2[0], 2 * cur[1] - prev_c2[1])
                else:
                    c1 = cur
                _tess_cubic(cur, c1, c2, end, 0.25, cur_poly)
                prev_c2 = c2
                cur = end
            last_cmd = cmd
            continue

        counts = {"Q": 4, "q": 4, "T": 2, "t": 2, "A": 7, "a": 7}
        cnt = counts.get(cmd)
        if cnt is None:
            break
        i = min(n, i + cnt)

    flush()
    return subpaths, closed


def circle_points(cx, cy, r, n=64):
    pts = [
        (cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n))
        for k in range(n)
    ]
    pts.append(pts[0])
    return pts


def rounded_rect_points(x, y, w, h, rx, ry, step=12):
    rx = min(rx, w / 2)
    ry = min(ry, h / 2)
    pts = []

    def arc(cx, cy, a0, a1):
        for k in range(step + 1):
            a = a0 + (a1 - a0) * k / step
            pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))

    arc(x + rx, y + ry, math.pi, 1.5 * math.pi)
    arc(x + w - rx, y + ry, 1.5 * math.pi, 2 * math.pi)
    arc(x + w - rx, y + h - ry, 0.0, 0.5 * math.pi)
    arc(x + rx, y + h - ry, 0.5 * math.pi, math.pi)
    return pts


def _winding(px, py, poly):
    winding = 0
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if yi <= py:
            if yj > py and (xj - xi) * (py - yi) - (yj - yi) * (px - xi) > 0:
                winding += 1
        elif yj <= py and (xj - xi) * (py - yi) - (yj - yi) * (px - xi) < 0:
            winding -= 1
        j = i
    return winding != 0


def _dist_to_segment(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0.0 and dy == 0.0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = 1.0 if t > 1.0 else (0.0 if t < 0.0 else t)
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def render(size, shapes):
    ss = size * SUPERSAMPLE
    k = ss / SVG_VIEW
    buf = bytearray(ss * ss * 4)

    for sh in shapes:
        if not sh.polylines:
            continue
        has_fill = sh.fill_color is not None
        has_stroke = sh.stroke_color is not None and sh.stroke_width > 0.0
        if not (has_fill or has_stroke):
            continue

        px_polys = []
        minx = miny = float("inf")
        maxx = maxy = float("-inf")
        for poly in sh.polylines:
            pxs = [(x * k, y * k) for x, y in poly]
            px_polys.append(pxs)
            for x, y in pxs:
                if x < minx:
                    minx = x
                if y < miny:
                    miny = y
                if x > maxx:
                    maxx = x
                if y > maxy:
                    maxy = y

        radius = 0.0
        if has_stroke:
            radius = max(sh.stroke_width / 2.0 * k, MIN_STROKE_PX / 2.0 * SUPERSAMPLE)
            minx -= radius + 1
            miny -= radius + 1
            maxx += radius + 1
            maxy += radius + 1

        ix0 = max(0, int(minx))
        iy0 = max(0, int(miny))
        ix1 = min(ss - 1, int(math.ceil(maxx)))
        iy1 = min(ss - 1, int(math.ceil(maxy)))

        if has_fill:
            for poly, is_closed in zip(sh.polylines, sh.closed):
                if not (is_closed and poly):
                    continue
                pxs = px_polys[sh.polylines.index(poly)]
                for py in range(iy0, iy1 + 1):
                    for px in range(ix0, ix1 + 1):
                        idx = (py * ss + px) * 4
                        if buf[idx + 3]:
                            continue
                        if _winding(px + 0.5, py + 0.5, pxs):
                            buf[idx] = sh.fill_color[0]
                            buf[idx + 1] = sh.fill_color[1]
                            buf[idx + 2] = sh.fill_color[2]
                            buf[idx + 3] = 255

        if has_stroke:
            segs = []
            for poly in px_polys:
                for i in range(len(poly) - 1):
                    segs.append((poly[i], poly[i + 1]))
            for py in range(iy0, iy1 + 1):
                for px in range(ix0, ix1 + 1):
                    idx = (py * ss + px) * 4
                    if buf[idx + 3]:
                        continue
                    pxp, pyp = px + 0.5, py + 0.5
                    hit = False
                    for (x1, y1), (x2, y2) in segs:
                        if _dist_to_segment(pxp, pyp, x1, y1, x2, y2) <= radius:
                            hit = True
                            break
                    if not hit:
                        for vx, vy in px_polys[0]:
                            if (vx - pxp) * (vx - pxp) + (vy - pyp) * (vy - pyp) <= radius * radius:
                                hit = True
                                break
                        if hit:
                            pass
                    if hit:
                        buf[idx] = sh.stroke_color[0]
                        buf[idx + 1] = sh.stroke_color[1]
                        buf[idx + 2] = sh.stroke_color[2]
                        buf[idx + 3] = 255

    return downsample(ss, buf, size)


def downsample(ss, buf, size):
    s = SUPERSAMPLE
    out = bytearray(size * size * 4)
    for y in range(size):
        for x in range(size):
            count = 0
            r = g = b = 0
            for dy in range(s):
                for dx in range(s):
                    i = ((y * s + dy) * ss + (x * s + dx)) * 4
                    if buf[i + 3]:
                        count += 1
                        r += buf[i]
                        g += buf[i + 1]
                        b += buf[i + 2]
            idx = (y * size + x) * 4
            if count:
                out[idx] = r // count
                out[idx + 1] = g // count
                out[idx + 2] = b // count
                out[idx + 3] = (255 * count) // (s * s)
    return out
