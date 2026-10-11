"""Stage 5: score every reply in responses.jsonl and write results.csv.

Costs nothing: it only reads the log. For each reply it pulls out the last
block of N lines of N 0/1 characters and compares it with the true grid.

  pixel_acc           fraction of pixels right, taking 1 = black as asked
  pixel_acc_inverted  the same with the reply's colours flipped; near 1.0 means
                      the model decoded the file but read the colours backwards
  named               rough keyword check that the reply names the shape
                      (blank for noise images, which have no name)

Pixel accuracy flatters sparse shapes: an all-white 8x8 reply scores about 0.8
on a digit. Trust `exact`, and the noise images, where chance is 0.5.
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
NAMES = {
    "digit_0": r"\b(0|zero|o)\b",
    "digit_1": r"\b(1|one)\b",
    "digit_7": r"\b(7|seven)\b",
    "shape_x": r"\b(x|cross)\b",
    "shape_square": r"\b(square|box|rectangle)\b",
    "shape_diagonal": r"\b(diagonal|backslash)\b",
    "shape_circle": r"\b(circle|ring|o)\b",
}

truth = {(im["name"], im["size"]): im["grid"] for im in json.loads((ROOT / "images" / "images.json").read_text())}


def find_grid(text, n):
    """Last run of n consecutive lines that are each n characters of 0/1."""
    lines = text.splitlines()
    rows = [re.sub(r"[\s`|]", "", line) for line in lines]
    ok = [bool(re.fullmatch(f"[01]{{{n}}}", r)) for r in rows]
    for end in range(len(rows), n - 1, -1):
        if all(ok[end - n : end]):
            return rows[end - n : end], "\n".join(lines[end:])
    return None, text


def accuracy(got, want):
    return sum(g == w for gr, wr in zip(got, want) for g, w in zip(gr, wr)) / len(want) ** 2


# a call resent at a larger token cap replaces its cut-off first attempt
latest = {}
for line in (ROOT / "responses.jsonl").read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    if "error" not in r:
        latest[r["model"], r["prompt_sha256"], r["effort"], r["run"]] = r

out_rows = []
for r in latest.values():
    want = truth[r["image"], r["size"]]
    grid, tail = find_grid(r["response"], r["size"])
    acc = inv = exact = ""
    if grid:
        acc = round(accuracy(grid, want), 3)
        inv = round(1 - acc, 3)
        exact = int(grid == want)
    named = ""
    if r["image"] in NAMES:
        named = int(bool(re.search(NAMES[r["image"]], tail, re.I)))
    conf = re.findall(r"confidence\W{0,20}(low|medium|high)|\b(low|medium|high)\W{0,5}confidence", r["response"], re.I)
    out_rows.append(
        {
            "model": r["model"],
            "effort": r["effort"],
            "run": r["run"],
            "image": r["image"],
            "size": r["size"],
            "format": r["format"],
            "exact": exact,
            "pixel_acc": acc,
            "pixel_acc_inverted": inv,
            "named": named,
            "confidence": "".join(conf[-1]).lower() if conf else "",
            "max_tokens": r["request"]["max_tokens"],
            "finish_reason": r["finish_reason"],
            "reasoning_tokens": r["reasoning_tokens"],
            "completion_tokens": r["usage"].get("completion_tokens"),
            "seconds": r["seconds"],
            "cost": round(r["cost"], 5),
        }
    )

with open(ROOT / "results.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out_rows[0]))
    w.writeheader()
    w.writerows(out_rows)

groups = defaultdict(list)
for row in out_rows:
    groups[row["model"], row["effort"], row["size"], row["format"]].append(row)
print(f"{'model':28} {'effort':6} {'size':>4} {'fmt':4} {'n':>2} {'exact':>5} {'acc':>5} {'inv':>5} {'no grid':>7} {'reason tok':>10} {'$':>7}")
for (model, effort, size, fmt), rows in sorted(groups.items()):
    scored = [x for x in rows if x["pixel_acc"] != ""]
    mean = lambda k: f"{sum(x[k] for x in scored) / len(scored):.2f}" if scored else "-"
    tok = [x["reasoning_tokens"] or 0 for x in rows]
    print(
        f"{model:28} {effort:6} {size:>4} {fmt:4} {len(rows):>2} {sum(x['exact'] or 0 for x in rows):>5} "
        f"{mean('pixel_acc'):>5} {mean('pixel_acc_inverted'):>5} {len(rows) - len(scored):>7} "
        f"{sum(tok) // len(tok):>10} {sum(x['cost'] for x in rows):>7.4f}"
    )
print(f"{len(out_rows)} replies scored -> results.csv")
