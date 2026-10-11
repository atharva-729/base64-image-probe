"""Stages 2-3: encode every test image several ways and write the prompts.

Reads images/images.json (from make_images.py) and writes:
  encodings.json                              every encoded string, per image
  prompts/<size>/<name>_<format>_<variant>.txt  ready-to-paste prompts
  token_counts.csv                            payload size and token estimates

Formats:
  grid  rows of 0/1 characters (control, not base64)
  pgm   binary PGM (P5): one byte per pixel, 0 = black, 255 = white
  pbm   binary PBM (P4): one bit per pixel, 1 = black, rows padded to a byte
  bmp   1-bit BMP: palette, bottom-up rows padded to 4 bytes
  png   1-bit PNG: DEFLATE-compressed
"""
import base64
import csv
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).parent
FORMATS = ("grid", "pgm", "pbm", "bmp", "png")
FORMAT_NAMES = {"pgm": "PGM (binary, P5)", "pbm": "PBM (binary, P4)", "bmp": "BMP", "png": "PNG"}
ASK = "tell me what the image shows. Then give your confidence (low/medium/high)."
SHOW_WORK = (
    "First reconstruct the pixel grid, writing one row per line using 1 for a "
    "black pixel and 0 for a white pixel. Then " + ASK
)

try:
    import tiktoken

    _enc = tiktoken.get_encoding("o200k_base")
    count_tokens = lambda s: len(_enc.encode(s))
except ImportError:
    count_tokens = lambda s: ""


def encode(grid, fmt):
    """grid: 2-D uint8 array, 1 = ink. Returns the payload string for the prompt."""
    n = len(grid)
    if fmt == "grid":
        return "\n".join("".join(map(str, row)) for row in grid)
    if fmt == "pgm":
        raw = f"P5\n{n} {n}\n255\n".encode() + ((1 - grid) * 255).astype(np.uint8).tobytes()
    elif fmt == "pbm":
        raw = f"P4\n{n} {n}\n".encode() + np.packbits(grid, axis=1).tobytes()
    else:
        buf = io.BytesIO()
        Image.fromarray((1 - grid) * 255).convert("1").save(buf, format=fmt.upper())
        raw = buf.getvalue()
    # round-trip check: the file must decode back to the same picture
    back = np.array(Image.open(io.BytesIO(raw)).convert("L")) < 128
    assert (back == grid.astype(bool)).all(), fmt
    return base64.b64encode(raw).decode()


def prompt(fmt, variant, n, payload):
    if fmt == "grid":
        what = {
            "blind": "The following is an image written as text.",
            "guided": f"The following is a {n}x{n} black-and-white image written as a text grid, one row per line (1 = black, 0 = white).",
        }
        what["showwork"] = what["guided"]
    else:
        what = {
            "blind": "The following is a base64-encoded image file.",
            "guided": f"The following is a base64-encoded {FORMAT_NAMES[fmt]} image file. The image is {n}x{n} pixels, black and white.",
        }
        what["showwork"] = what["guided"]
    if variant == "showwork":
        task = "Do not use any tools or run any code. " + SHOW_WORK
    else:
        task = "Without using any tools, " + ASK
    return f"{what[variant]} {task}\n\n{payload}\n"


images = json.loads((ROOT / "images" / "images.json").read_text())
encodings, token_rows = [], []
for im in images:
    name, n = im["name"], im["size"]
    grid = np.array([[int(c) for c in row] for row in im["grid"]], dtype=np.uint8)
    entry = {"name": name, "size": n}
    out = ROOT / "prompts" / f"{n}x{n}"
    out.mkdir(parents=True, exist_ok=True)
    for fmt in FORMATS:
        payload = entry[fmt] = encode(grid, fmt)
        for variant in ("blind", "guided", "showwork"):
            (out / f"{name}_{fmt}_{variant}.txt").write_text(prompt(fmt, variant, n, payload), newline="\n")
        token_rows.append([name, n, fmt, len(payload), count_tokens(payload), round(n * n / 750, 2)])
    encodings.append(entry)

(ROOT / "encodings.json").write_text(json.dumps(encodings, indent=1))

with open(ROOT / "token_counts.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["image", "size", "format", "payload_chars", "payload_tokens_o200k", "native_image_tokens_claude_formula"])
    w.writerows(token_rows)

print(f"wrote {len(images) * len(FORMATS) * 3} prompts for {len(images)} images")
