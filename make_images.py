"""Stage 1: build the fixed test set from the README.

Seven pure black-and-white images (digits 1, 7, 0; shapes X, square, diagonal,
circle), each rasterised natively at 8x8, 16x16 and 32x32, plus two random-noise
images per size. Noise has no shape to guess, so only real decoding scores on it.

Outputs, under images/:
  raw/<name>_<size>.png      true-size 1-bit image (black ink on white)
  preview/<name>_<size>.png  same image upscaled to 256x256 for viewing
  contact_sheet.png          all of them in one grid, labelled
  images.json                0/1 pixel grid for every image (1 = ink)
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SIZES = (8, 16, 32)
HALF_STROKE = 0.07  # in unit-square units; gives a 1px stroke at 8x8
PREVIEW = 256
OUT = Path(__file__).parent / "images"

# Shapes are polylines whose points are pixel indices on the 8x8 grid
# (x = column, y = row). They are mapped to the unit square, so the same
# definition renders at any size.
POLYLINES = {
    "digit_1": [[(2, 2), (4, 0), (4, 7)], [(2, 7), (6, 7)]],
    "digit_7": [[(1, 0), (6, 0), (3, 7)]],
    "digit_0": [[(3, 0), (4, 0), (5, 1), (5, 6), (4, 7), (3, 7), (2, 6), (2, 1), (3, 0)]],
    "shape_x": [[(0, 0), (7, 7)], [(7, 0), (0, 7)]],
    "shape_square": [[(1, 1), (6, 1), (6, 6), (1, 6), (1, 1)]],
    "shape_diagonal": [[(0, 0), (7, 7)]],
}
CIRCLE_RADIUS = 3.5 / 8  # ring centred on the image
NOISE_SEEDS = {"noise_a": 1, "noise_b": 2}  # each pixel black with probability 1/2


def pixel_centres(n):
    c = (np.arange(n) + 0.5) / n
    return np.meshgrid(c, c)  # x, y


def segment_distance(x, y, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = np.clip(((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy), 0, 1)
    return np.hypot(x - (ax + t * dx), y - (ay + t * dy))


def render(name, n):
    if name in NOISE_SEEDS:
        return np.random.default_rng([NOISE_SEEDS[name], n]).integers(0, 2, (n, n), dtype=np.uint8)
    x, y = pixel_centres(n)
    if name == "shape_circle":
        dist = np.abs(np.hypot(x - 0.5, y - 0.5) - CIRCLE_RADIUS)
    else:
        dist = np.full((n, n), np.inf)
        for line in POLYLINES[name]:
            pts = [((px + 0.5) / 8, (py + 0.5) / 8) for px, py in line]
            for a, b in zip(pts, pts[1:]):
                dist = np.minimum(dist, segment_distance(x, y, a, b))
    return (dist <= HALF_STROKE + 1e-9).astype(np.uint8)  # 1 = ink


names = list(POLYLINES) + ["shape_circle"] + list(NOISE_SEEDS)
(OUT / "raw").mkdir(parents=True, exist_ok=True)
(OUT / "preview").mkdir(exist_ok=True)

manifest = []
tiles = {}
for name in names:
    for n in SIZES:
        grid = render(name, n)
        img = Image.fromarray((1 - grid) * 255).convert("1")
        fname = f"{name}_{n}.png"
        img.save(OUT / "raw" / fname)
        big = img.resize((PREVIEW, PREVIEW), Image.NEAREST)
        big.save(OUT / "preview" / fname)
        tiles[name, n] = big
        manifest.append({"name": name, "size": n, "grid": ["".join(map(str, r)) for r in grid]})

(OUT / "images.json").write_text(json.dumps(manifest, indent=1))

# contact sheet: one column per image, one row per size
pad, label_h = 12, 18
sheet = Image.new("L", (pad + len(names) * (PREVIEW + pad), pad + len(SIZES) * (PREVIEW + label_h + pad)), 255)
draw = ImageDraw.Draw(sheet)
for col, name in enumerate(names):
    for row, n in enumerate(SIZES):
        x, y = pad + col * (PREVIEW + pad), pad + row * (PREVIEW + label_h + pad)
        draw.text((x, y), f"{name}  {n}x{n}", fill=0)
        sheet.paste(tiles[name, n], (x, y + label_h))
        draw.rectangle([x - 1, y + label_h - 1, x + PREVIEW, y + label_h + PREVIEW], outline=160)
sheet.save(OUT / "contact_sheet.png")

print(f"wrote {len(manifest)} images to {OUT}")
