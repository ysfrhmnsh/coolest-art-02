#!/usr/bin/env python3
"""Make the coolest art -- entry program v2 (Python 3.13, standard library only).

"Dragon Over the Burning Mountain": a great dragon silhouetted against a
blood moon, wings spread, crossing the sky above an erupting volcano. Lava
streams run down the cone, embers rise into the red sky, and a river of fire
cuts the foreground. Pure procedural geometry -- silhouettes, gradients,
noise -- so the craft is exact: no garbled text, no broken anatomy (the
dragon is a silhouette, the classic "dragon crossing the moon" shot). One
clear focal shape (dragon + moon) reads at 300 pixels wide.

Deterministic: fixed seed, no clock, no network, no unseeded randomness.
Writes /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png), 1024x1024,
well under 1 MiB. PNG encoder written by hand with stdlib zlib + struct.
"""

import math
import os
import random
import struct
import zlib

W = H = 1024
SEED = 20261114

# ---------------------------------------------------------------- palette
SKY_TOP = (18, 4, 10)
SKY_MID = (84, 16, 22)
SKY_LOW = (186, 62, 26)
MOON = (246, 222, 176)
MOON_DARK = (222, 196, 152)
MOON_HALO = (255, 170, 90)
SIL = (10, 6, 8)            # near-black silhouette
SIL_FAR = (16, 8, 10)       # far wing / far ridge (slightly lighter)
BONE = (44, 16, 18)         # wing bones, subtle internal detail
RIM = (255, 116, 36)        # rim light, moon side
LAVA = (255, 140, 28)
LAVA_CORE = (255, 205, 90)
LAVA_DEEP = (190, 56, 16)
SMOKE = (52, 24, 26)
SMOKE_HOT = (120, 44, 26)
EMBER = (255, 150, 44)
GROUND = (12, 6, 8)

# geometry
MOON_CX, MOON_CY, MOON_R = 700, 230, 210
VOLC_L, VOLC_R = 360, 500      # crater rim x range
VOLC_Y = 655                   # crater rim y
CRATER_CX, CRATER_CY = 430, 648

# ---------------------------------------------------------------- helpers
def clamp(v, lo=0, hi=255):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def lerp3(c1, c2, t):
    return (lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t))


def smooth(t):
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    return t * t * (3.0 - 2.0 * t)


def ramp(stops, t):
    """Piecewise-linear colour ramp; stops = [(pos, r, g, b), ...]."""
    if t <= stops[0][0]:
        return stops[0][1:]
    for i in range(1, len(stops)):
        if t <= stops[i][0]:
            p0, p1 = stops[i - 1], stops[i]
            f = (t - p0[0]) / (p1[0] - p0[0])
            return lerp3(p0[1:], p1[1:], f)
    return stops[-1][1:]


# ---------------------------------------------------------------- value noise
_rng = random.Random(SEED)
_NG = 96
_grid = [[_rng.random() for _ in range(_NG + 1)] for _ in range(_NG + 1)]


def noise(x, y):
    """Smooth value noise, x/y in grid cells. Returns 0..1."""
    xi = int(math.floor(x))
    yi = int(math.floor(y))
    xf = x - xi
    yf = y - yi
    xi %= _NG
    yi %= _NG
    x0, y0 = xi, yi
    x1, y1 = xi + 1, yi + 1
    u = smooth(xf)
    v = smooth(yf)
    g = _grid
    a = lerp(g[y0][x0], g[y0][x1], u)
    b = lerp(g[y1][x0], g[y1][x1], u)
    return lerp(a, b, v)


def fbm(x, y):
    """Two-octave fractal noise, 0..1."""
    return 0.65 * noise(x, y) + 0.35 * noise(x * 2.13 + 7.7, y * 2.13 + 3.1)


# ---------------------------------------------------------------- PNG writer
def _png_chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)


def _filter_row(filter_type, row, prev):
    """Apply a PNG row filter; return filtered bytes."""
    n = len(row)
    out = bytearray(n)
    if filter_type == 0:
        return bytes(row)
    if filter_type == 1:  # Sub
        for i in range(n):
            a = row[i - 3] if i >= 3 else 0
            out[i] = (row[i] - a) & 0xFF
    elif filter_type == 2:  # Up
        for i in range(n):
            out[i] = (row[i] - prev[i]) & 0xFF
    elif filter_type == 3:  # Average
        for i in range(n):
            a = row[i - 3] if i >= 3 else 0
            out[i] = (row[i] - ((a + prev[i]) >> 1)) & 0xFF
    else:  # Paeth
        for i in range(n):
            a = row[i - 3] if i >= 3 else 0
            b = prev[i]
            c = prev[i - 3] if i >= 3 else 0
            p = a + b - c
            pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
            pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
            out[i] = (row[i] - pr) & 0xFF
    return bytes(out)


def _filter_score(frow):
    """Heuristic: sum of absolute values of signed bytes."""
    return sum(b if b < 128 else 256 - b for b in frow)


def write_png(path, px, w, h):
    """px: bytearray of RGB triples, w*h*3. Adaptive per-row filter."""
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = bytearray()
    prev = bytes(w * 3)
    stride = w * 3
    for y in range(h):
        row = bytes(px[y * stride:(y + 1) * stride])
        best_f, best_s = 0, None
        for f in (0, 1, 2, 3, 4):
            cand = _filter_row(f, row, prev)
            s = _filter_score(cand)
            if best_s is None or s < best_s:
                best_f, best_s, best_row = f, s, cand
        raw.append(best_f)
        raw += best_row
        prev = row
    data = b"\x89PNG\r\n\x1a\n"
    data += _png_chunk(b"IHDR", ihdr)
    data += _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    data += _png_chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(data)
    return len(data)

# ---------------------------------------------------------------- drawing primitives
def set_px(px, x, y, col):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        px[i], px[i + 1], px[i + 2] = col[0], col[1], col[2]


def blend_px(px, x, y, col, a):
    """Blend col over the pixel at (x, y) with alpha a (0..1)."""
    if 0 <= x < W and 0 <= y < H and a > 0.0:
        i = (y * W + x) * 3
        px[i] = int(lerp(px[i], col[0], a))
        px[i + 1] = int(lerp(px[i + 1], col[1], a))
        px[i + 2] = int(lerp(px[i + 2], col[2], a))


def fill_circle(px, cx, cy, r, col, alpha=1.0):
    r = int(r)
    if r <= 0:
        return
    for y in range(max(0, cy - r), min(H - 1, cy + r) + 1):
        dy = y - cy
        dx = int(math.sqrt(max(0, r * r - dy * dy)))
        x0 = max(0, cx - dx)
        x1 = min(W - 1, cx + dx)
        for x in range(x0, x1 + 1):
            if alpha >= 1.0:
                set_px(px, x, y, col)
            else:
                blend_px(px, x, y, col, alpha)


def fill_ellipse(px, cx, cy, rx, ry, col, alpha=1.0):
    rx = int(rx)
    ry = int(ry)
    if rx <= 0 or ry <= 0:
        return
    for y in range(max(0, cy - ry), min(H - 1, cy + ry) + 1):
        dy = (y - cy) / float(ry)
        dx = int(rx * math.sqrt(max(0.0, 1.0 - dy * dy)))
        x0 = max(0, cx - dx)
        x1 = min(W - 1, cx + dx)
        for x in range(x0, x1 + 1):
            if alpha >= 1.0:
                set_px(px, x, y, col)
            else:
                blend_px(px, x, y, col, alpha)


def fill_poly(px, pts, col, alpha=1.0):
    """Scanline fill for a (possibly concave) polygon. pts = [(x, y), ...]."""
    if len(pts) < 3:
        return
    ys = [p[1] for p in pts]
    y0 = max(0, int(min(ys)))
    y1 = min(H - 1, int(max(ys)) + 1)
    n = len(pts)
    for y in range(y0, y1 + 1):
        xs = []
        for k in range(n):
            x1, y1p = pts[k]
            x2, y2p = pts[(k + 1) % n]
            if (y1p <= y < y2p) or (y2p <= y < y1p):
                t = (y - y1p) / float(y2p - y1p)
                xs.append(x1 + t * (x2 - x1))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            xa = max(0, int(math.ceil(xs[k])))
            xb = min(W - 1, int(math.floor(xs[k + 1])))
            for x in range(xa, xb + 1):
                if alpha >= 1.0:
                    set_px(px, x, y, col)
                else:
                    blend_px(px, x, y, col, alpha)


def stroke(px, x0, y0, x1, y1, w, col, alpha=1.0):
    """Thick line: stamp circles along the segment."""
    dist = math.hypot(x1 - x0, y1 - y0)
    steps = max(1, int(dist / max(1.0, w * 0.45)))
    r = w / 2.0
    for k in range(steps + 1):
        t = k / float(steps)
        fill_circle(px, int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t),
                    r, col, alpha)


def tube(px, pts, radii, col, alpha=1.0):
    """Tapering tube through pts with per-point radii (arc-length interp)."""
    # build dense polyline with cumulative lengths
    seg = []
    total = 0.0
    for k in range(len(pts) - 1):
        d = math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1])
        seg.append(d)
        total += d
    # sample every ~3 px along the tube
    n = max(2, int(total / 3.0))
    for s in range(n + 1):
        target = total * s / float(n)
        acc = 0.0
        for k in range(len(pts) - 1):
            if acc + seg[k] >= target or k == len(pts) - 2:
                f = 0.0 if seg[k] == 0 else (target - acc) / seg[k]
                f = max(0.0, min(1.0, f))
                x = pts[k][0] + (pts[k + 1][0] - pts[k][0]) * f
                y = pts[k][1] + (pts[k + 1][1] - pts[k][1]) * f
                r = radii[k] + (radii[k + 1] - radii[k]) * f
                fill_circle(px, int(x), int(y), r, col, alpha)
                break
            acc += seg[k]


# ---------------------------------------------------------------- renderer
def render():
    px = bytearray(W * H * 3)
    rng = random.Random(SEED + 2)

    # ---- sky: vertical gradient, warm near the horizon and the volcano ----
    glow_x = [0.0] * W
    for x in range(W):
        d = (x - CRATER_CX) / 300.0
        glow_x[x] = math.exp(-d * d)
    for y in range(H):
        t = y / float(H)
        if t < 0.42:
            base = lerp3(SKY_TOP, SKY_MID, t / 0.42)
        else:
            base = lerp3(SKY_MID, SKY_LOW, (t - 0.42) / 0.58)
        # warm lift above the volcano, strongest near the horizon
        warm = smooth((y - 420.0) / 340.0) * 0.5
        off = y * W * 3
        for x in range(W):
            w = warm * glow_x[x]
            r = lerp(base[0], 232, w * 0.55)
            g = lerp(base[1], 96, w * 0.55)
            b = lerp(base[2], 34, w * 0.55)
            i = off + x * 3
            px[i] = int(r) if r < 255 else 255
            px[i + 1] = int(g) if g < 255 else 255
            px[i + 2] = int(b) if b < 255 else 255

    # ---- faint stars in the dark upper sky ----
    for _ in range(140):
        x = rng.randrange(0, W)
        y = rng.randrange(0, 330)
        b = rng.random()
        v = 70 + int(80 * b)
        i = (y * W + x) * 3
        if v > px[i]:
            px[i] = px[i + 1] = px[i + 2] = v

    # ---- moon halo (radial falloff) + disk + craters ----
    halo_r2 = 330.0 * 330.0
    for y in range(max(0, MOON_CY - 330), min(H, MOON_CY + 330) + 1):
        dy = y - MOON_CY
        off = y * W * 3
        for x in range(max(0, MOON_CX - 330), min(W, MOON_CX + 330) + 1):
            dx = x - MOON_CX
            d2 = dx * dx + dy * dy
            if d2 < halo_r2:
                h = 1.0 - d2 / halo_r2
                h *= h
                i = off + x * 3
                px[i] = clamp(px[i] + int(96 * h))
                px[i + 1] = clamp(px[i + 1] + int(58 * h))
                px[i + 2] = clamp(px[i + 2] + int(26 * h))
    for y in range(max(0, MOON_CY - MOON_R), min(H, MOON_CY + MOON_R) + 1):
        dy = y - MOON_CY
        off = y * W * 3
        for x in range(max(0, MOON_CX - MOON_R), min(W, MOON_CX + MOON_R) + 1):
            dx = x - MOON_CX
            d2 = dx * dx + dy * dy
            if d2 > MOON_R * MOON_R:
                continue
            rn = math.sqrt(d2) / MOON_R
            # limb darkening + subtle mottling
            m = 1.0 - 0.16 * rn * rn
            mott = 0.94 + 0.06 * noise(x * 0.03, y * 0.03)
            i = off + x * 3
            px[i] = int(MOON[0] * m * mott)
            px[i + 1] = int(MOON[1] * m * mott)
            px[i + 2] = int(MOON[2] * m * mott)
    # craters: soft darker blotches
    craters = [(626, 169, 35, 27), (734, 142, 24, 19), (680, 264, 40, 30),
               (774, 277, 22, 16), (599, 277, 19, 14), (761, 203, 16, 12),
               (666, 196, 14, 11)]
    for (cx, cy, rx, ry) in craters:
        fill_ellipse(px, cx, cy, rx, ry, MOON_DARK, alpha=0.55)

    # ---- distant mountain ridges (left + right), dark against the sky ----
    def ridge(x0, x1, base_y, amp, seed, col):
        top = []
        for x in range(x0, x1 + 1, 6):
            t = base_y + (noise(x * 0.011, seed) - 0.5) * amp
            top.append((x, int(t)))
        pts = top + [(x1, H), (x0, H)]
        fill_poly(px, pts, col)

    ridge(0, 300, 700, 120, 3.3, SIL_FAR)
    ridge(760, W, 720, 110, 8.8, SIL_FAR)

    # ---- volcano cone (noise-wobbled slopes) ----
    left_slope = []
    for k in range(0, 21):
        t = k / 20.0
        x = int(40 + (VOLC_L - 40) * t)
        y = int(H - (H - VOLC_Y) * t + (noise(x * 0.02, 4.4) - 0.5) * 26)
        left_slope.append((x, y))
    right_slope = []
    for k in range(0, 21):
        t = k / 20.0
        x = int(VOLC_R + (900 - VOLC_R) * t)
        y = int(VOLC_Y + (H - VOLC_Y) * t + (noise(x * 0.02, 6.1) - 0.5) * 26)
        right_slope.append((x, y))
    # cone with a vertical gradient: lighter near the crater, darker at base
    def slope_x(slope_pts, y):
        for k in range(len(slope_pts) - 1):
            (xa, ya), (xb, yb) = slope_pts[k], slope_pts[k + 1]
            if (ya <= y <= yb) or (yb <= y <= ya):
                t = 0.0 if yb == ya else (y - ya) / float(yb - ya)
                return xa + (xb - xa) * t
        return slope_pts[-1][0]
    for y in range(VOLC_Y, H):
        xl = int(slope_x(left_slope, y))
        xr = int(slope_x(right_slope, y))
        f = (y - VOLC_Y) / float(H - VOLC_Y)
        col = tuple(int(c) for c in lerp3((26, 11, 13), (8, 4, 6), f))
        for x in range(max(0, xl), min(W - 1, xr) + 1):
            set_px(px, x, y, col)

    # ---- crater glow (radial, above the crater) ----
    glow_r2 = 260.0 * 260.0
    for y in range(max(0, CRATER_CY - 260), min(H, CRATER_CY + 120) + 1):
        dy = y - CRATER_CY
        off = y * W * 3
        for x in range(max(0, CRATER_CX - 260), min(W, CRATER_CX + 260) + 1):
            dx = x - CRATER_CX
            d2 = dx * dx + dy * dy
            if d2 < glow_r2:
                h = 1.0 - d2 / glow_r2
                h *= h
                i = off + x * 3
                px[i] = clamp(px[i] + int(150 * h))
                px[i + 1] = clamp(px[i + 1] + int(70 * h))
                px[i + 2] = clamp(px[i + 2] + int(18 * h))

    # ---- crater lava pool (bright ellipse, yellow core) ----
    fill_ellipse(px, CRATER_CX, CRATER_CY, 78, 17, LAVA_DEEP)
    fill_ellipse(px, CRATER_CX, CRATER_CY, 66, 13, LAVA)
    fill_ellipse(px, CRATER_CX, CRATER_CY - 2, 44, 8, LAVA_CORE)

    # ---- lava streams down the cone (jagged, glowing) ----
    def lava_stream(x0, y0, x1, y1, seed):
        path = []
        steps = 14
        for k in range(steps + 1):
            t = k / float(steps)
            x = int(x0 + (x1 - x0) * t + (noise(k * 0.9, seed) - 0.5) * 34)
            y = int(y0 + (y1 - y0) * t)
            path.append((x, y))
        # soft glow pass, then main, then hot core
        for k in range(len(path) - 1):
            stroke(px, path[k][0], path[k][1], path[k + 1][0],
                   path[k + 1][1], 24, LAVA_DEEP, alpha=0.45)
        for k in range(len(path) - 1):
            stroke(px, path[k][0], path[k][1], path[k + 1][0],
                   path[k + 1][1], 11, LAVA)
        for k in range(len(path) - 1):
            stroke(px, path[k][0], path[k][1], path[k + 1][0],
                   path[k + 1][1], 5, LAVA_CORE)

    lava_stream(392, 656, 300, 1000, 11.1)
    lava_stream(438, 664, 430, 1006, 22.2)
    lava_stream(486, 656, 560, 998, 33.3)
    lava_stream(470, 660, 700, 1002, 44.4)

    # ---- foreground ground + lava river ----
    river_top = []
    for x in range(0, W + 1, 8):
        river_top.append((x, int(946 + (noise(x * 0.015, 2.2) - 0.5) * 22)))
    river = river_top + [(W, H), (0, H)]
    fill_poly(px, river, LAVA_DEEP)
    # hot core band inside the river
    core_top = []
    for x in range(0, W + 1, 8):
        core_top.append((x, int(968 + (noise(x * 0.015, 9.9) - 0.5) * 16)))
    core = core_top + [(W, H), (0, H)]
    fill_poly(px, core, LAVA)
    # yellow streaks in the river
    for _ in range(40):
        gx = rng.randrange(20, W - 60)
        gy = rng.randrange(972, 1012)
        ln = rng.randrange(18, 60)
        for k in range(ln):
            blend_px(px, gx + k, gy, LAVA_CORE, 0.75)
    # dark rocks half-submerged at the river's top edge, rim-lit by lava
    for (rx, ry, s) in [(120, 952, 26), (330, 950, 34), (660, 954, 24), (880, 950, 30)]:
        rock = [(rx - s, ry + 4), (rx - s * 0.5, ry - s * 0.55),
                (rx + s * 0.4, ry - s * 0.7), (rx + s, ry + 2), (rx + s * 0.6, ry + 8)]
        fill_poly(px, [(int(a), int(b)) for (a, b) in rock], GROUND)
        # thin orange rim on the rock's top edge
        stroke(px, int(rx - s * 0.5), int(ry - s * 0.55), int(rx + s * 0.4),
               int(ry - s * 0.7), 3, LAVA, alpha=0.8)

    # ---- smoke plume above the crater (billowing, drifting right) ----
    puffs = []
    for k in range(14):
        t = k / 13.0
        cx = int(CRATER_CX + 15 * t + 40 * t * t + (noise(k * 0.7, 1.1) - 0.5) * 26)
        cy = int(CRATER_CY - 30 - 280 * t)
        r = int(30 + 90 * t)
        puffs.append((cx, cy, r, t))
    for (cx, cy, r, t) in puffs:
        col = lerp3(SMOKE_HOT, SMOKE, t)
        # soft halo circle, then textured inner circles (no hard disk edges)
        fill_circle(px, cx, cy, int(r * 1.15), col, alpha=0.10)
        for _ in range(5):
            ox = int((rng.random() - 0.5) * r * 0.9)
            oy = int((rng.random() - 0.5) * r * 0.6)
            rr = int(r * (0.5 + rng.random() * 0.35))
            a = 0.20 + 0.22 * fbm((cx + ox) * 0.02, (cy + oy) * 0.02)
            fill_circle(px, cx + ox, cy + oy, rr, col, alpha=min(0.55, a))

    # ---- embers rising from the crater (behind the dragon) ----
    for _ in range(170):
        t = rng.random()
        ex = int(CRATER_CX + (rng.random() - 0.5) * (120 + 420 * t))
        ey = int(CRATER_CY - 20 - 470 * t + (rng.random() - 0.5) * 30)
        s = 1 if rng.random() < 0.7 else 2
        v = 150 + int(105 * rng.random())
        a = 0.45 + 0.45 * rng.random()
        col = (255, int(120 + 60 * rng.random()), 40)
        for dx in range(-s, s + 1):
            for dy in range(-s, s + 1):
                blend_px(px, ex + dx, ey + dy, col, a * (0.7 if abs(dx) + abs(dy) > 1 else 1.0))

    # ---- the dragon (rim-light pass, then silhouette pass) ----
    # Body crosses the big moon, so the whole silhouette reads against it.
    SPINE = [(280, 445), (380, 415), (480, 380), (570, 340),
             (650, 305), (720, 272), (780, 248)]
    RADII = [4, 9, 15, 24, 33, 38, 30, 22]
    NEAR_WING = [(640, 310), (700, 215), (780, 150), (860, 110), (810, 150),
                 (760, 205), (700, 240), (650, 280), (600, 310), (560, 330),
                 (540, 325)]
    FAR_WING = [(600, 320), (540, 230), (480, 150), (430, 100), (465, 175),
                (500, 235), (535, 285), (570, 312)]

    def off(pts, ox, oy):
        return [(x + ox, y + oy) for (x, y) in pts]

    def draw_dragon(ox, oy, col, far_col):
        # far wing (behind the body)
        fill_poly(px, off(FAR_WING, ox, oy), far_col)
        # tail spade
        fill_poly(px, off([(283, 443), (258, 428), (244, 443), (258, 458)], ox, oy), col)
        # body + neck tube
        tube(px, off(SPINE, ox, oy), RADII, col)
        # head + snout wedge
        fill_ellipse(px, 812 + ox, 240 + oy, 34, 22, col)
        fill_poly(px, off([(828, 224), (902, 238), (884, 252), (832, 256)], ox, oy), col)
        # horns (tapered, swept back)
        tube(px, off([(795, 222), (748, 182), (712, 160)], ox, oy), [10, 6, 2], col)
        tube(px, off([(808, 230), (766, 196), (736, 178)], ox, oy), [8, 5, 2], col)
        # neck + back spikes
        for (sx, sy, hh) in [(480, 380, 16), (570, 340, 18), (650, 305, 18),
                             (720, 272, 14), (380, 415, 12)]:
            fill_poly(px, off([(sx - 7, sy - 2), (sx + 7, sy - 2), (sx - 4, sy - hh)], ox, oy), col)
        # legs, tucked in flight
        tube(px, off([(600, 340), (560, 400), (585, 445)], ox, oy), [15, 11, 7], col)
        tube(px, off([(690, 305), (672, 355), (695, 390)], ox, oy), [12, 9, 6], col)
        # claws
        for (cx, cy) in [(585, 445), (695, 390)]:
            fill_poly(px, off([(cx - 6, cy), (cx + 6, cy), (cx + 2, cy + 12)], ox, oy), col)
            fill_poly(px, off([(cx - 2, cy + 2), (cx + 10, cy + 2), (cx + 8, cy + 12)], ox, oy), col)

    draw_dragon(6, -5, RIM, (220, 95, 30))
    draw_dragon(0, 0, SIL, SIL_FAR)
    # no wing bones: the scalloped membrane reads cleaner as a pure silhouette
    # the eye: a burning ember-orange dot
    fill_circle(px, 815, 232, 8, (255, 120, 30), alpha=0.35)
    fill_circle(px, 815, 232, 3, (255, 170, 60))

    # ---- embers in front of the dragon (brighter, some with trails) ----
    for _ in range(120):
        t = rng.random()
        ex = int(CRATER_CX + (rng.random() - 0.5) * (200 + 480 * t))
        ey = int(CRATER_CY - 10 - 520 * t + (rng.random() - 0.5) * 34)
        s = 1 if rng.random() < 0.6 else 2
        col = (255, int(130 + 70 * rng.random()), 44)
        a = 0.6 + 0.4 * rng.random()
        fill_circle(px, ex, ey, s, col, alpha=a)
        if rng.random() < 0.35:  # rising trail
            ln = rng.randrange(3, 9)
            for k in range(1, ln + 1):
                blend_px(px, ex, ey + k, col, a * (1.0 - k / float(ln)) * 0.7)
    # a few big glowing embers
    for _ in range(7):
        t = rng.random()
        ex = int(CRATER_CX + (rng.random() - 0.5) * (150 + 350 * t))
        ey = int(CRATER_CY - 30 - 420 * t)
        fill_circle(px, ex, ey, 9, (255, 120, 30), alpha=0.25)
        fill_circle(px, ex, ey, 4, (255, 170, 60))

    # ---- vignette ----
    maxd2 = (512.0 * 512.0) * 2.0
    vig = [1.0 - 0.26 * smooth(max(0.0, (k / 255.0 - 0.50) / 0.50))
           for k in range(256)]
    for y in range(H):
        dy = y - 512
        off = y * W * 3
        for x in range(W):
            dx = x - 512
            k = int((dx * dx + dy * dy) / maxd2 * 255.0)
            f = vig[k] if k < 256 else vig[255]
            i = off + x * 3
            px[i] = int(px[i] * f)
            px[i + 1] = int(px[i + 1] * f)
            px[i + 2] = int(px[i + 2] * f)

    return px


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    px = render()
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path, px, W, H)
    print(f"wrote {path} ({size} bytes, {W}x{H})")


if __name__ == "__main__":
    main()
