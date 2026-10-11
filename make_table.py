"""Stage 6: the model x format comparison, as two SVG heatmaps and a table.

Costs nothing: it only reads results.csv (run score.py first). Writes, under
results/api_runs/:
  accuracy.svg  share of images decoded pixel-for-pixel
  cost.svg      average cost of one call
  table.md      the same numbers as a Markdown table

Only 8x8 images that every model was given are counted, so the rows compare
like with like. A decode counts if every pixel is right, including when the
model has black and white swapped: that is a misreading of the colour
convention, not a failure to decode.
"""
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "results" / "api_runs"
IMAGES = ("digit_7", "noise_a")
FORMATS = (("grid", "Text grid"), ("pbm", "PBM"), ("pgm", "PGM"), ("bmp", "BMP"), ("png", "PNG"))
# one row per model at the effort where it reasons, plus a no-reasoning baseline
ROWS = (
    ("anthropic/claude-sonnet-5.5", "high", "Claude Sonnet 5.5", "high effort"),
    ("openai/gpt-6-sol", "medium", "GPT-6 Sol", "medium effort"),
    ("openai/gpt-6-luna", "high", "GPT-6 Luna", "high effort"),
    ("google/gemini-3.8-flash", "low", "Gemini 3.8 Flash", "low effort"),
    ("openai/gpt-6-luna", "none", "GPT-6 Luna", "reasoning off"),
)
RAMP = ("#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95")
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#d9d8d2"

cells = defaultdict(list)
for r in csv.DictReader(open(ROOT / "results.csv")):
    if r["size"] == "8" and r["image"] in IMAGES:
        cells[r["model"], r["effort"], r["format"]].append(r)


def summary(rows):
    n = len(rows)
    flipped = sum(r["pixel_acc_inverted"] == "1.0" for r in rows)
    return {
        "n": n,
        "decoded": sum(r["exact"] == "1" for r in rows) + flipped,
        "flipped": flipped,
        "cut_off": sum(r["finish_reason"] == "length" and r["pixel_acc"] == "" for r in rows),
        "declined": sum(r["finish_reason"] != "length" and r["pixel_acc"] == "" for r in rows),
        "cost": sum(float(r["cost"]) for r in rows) / n,
        "tokens": sum(int(r["reasoning_tokens"] or 0) for r in rows) / n,
        "seconds": sum(float(r["seconds"]) for r in rows) / n,
    }


table = {(m, e, f): summary(rows) for (m, e, f), rows in cells.items()}
max_cost = max(s["cost"] for (m, e, f), s in table.items() if (m, e) in {(r[0], r[1]) for r in ROWS})


def money(x):
    return f"${x:.3f}" if x >= 0.0005 else "under $0.001"


def heatmap(path, title, subtitle, legend, value, lines):
    """value(s) -> 0..1 for the fill; lines(s) -> the two text lines in a cell."""
    left, top, cw, ch, gap = 190, 96, 152, 62, 2
    width = left + len(FORMATS) * cw + 24
    height = top + len(ROWS) * ch + 64
    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'font-family="system-ui, -apple-system, Segoe UI, Helvetica, Arial, sans-serif" role="img" aria-label="{title}">',
        f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>',
        f'<text x="24" y="34" font-size="17" font-weight="600" fill="{INK}">{title}</text>',
        f'<text x="24" y="56" font-size="12.5" fill="{MUTED}">{subtitle}</text>',
    ]
    for j, (_, name) in enumerate(FORMATS):
        o.append(f'<text x="{left + j * cw + cw / 2}" y="{top - 10}" font-size="12.5" font-weight="600" fill="{INK}" text-anchor="middle">{name}</text>')
    for i, (model, effort, name, note) in enumerate(ROWS):
        y = top + i * ch
        o.append(f'<text x="24" y="{y + ch / 2 - 3}" font-size="13" font-weight="600" fill="{INK}">{name}</text>')
        o.append(f'<text x="24" y="{y + ch / 2 + 14}" font-size="11.5" fill="{MUTED}">{note}</text>')
        for j, (fmt, fname) in enumerate(FORMATS):
            x = left + j * cw
            s = table.get((model, effort, fmt))
            box = f'x="{x + gap / 2}" y="{y + gap / 2}" width="{cw - gap}" height="{ch - gap}" rx="4"'
            if not s:
                o.append(f'<rect {box} fill="{SURFACE}" stroke="{GRID}" stroke-dasharray="3 3"/>')
                o.append(f'<text x="{x + cw / 2}" y="{y + ch / 2 + 4}" font-size="11.5" fill="{MUTED}" text-anchor="middle">not run</text>')
                continue
            step = round(max(0, min(1, value(s))) * (len(RAMP) - 1))
            ink = SURFACE if step >= 6 else INK
            a, b = lines(s)
            tip = f"{name} ({note}), {fname}: {s['decoded']} of {s['n']} decoded, {money(s['cost'])} per call, {s['tokens']:.0f} reasoning tokens, {s['seconds']:.0f} s"
            o.append(f'<g><title>{tip}</title><rect {box} fill="{RAMP[step]}"/>')
            o.append(f'<text x="{x + cw / 2}" y="{y + ch / 2 - 2}" font-size="15" font-weight="600" fill="{ink}" text-anchor="middle">{a}</text>')
            o.append(f'<text x="{x + cw / 2}" y="{y + ch / 2 + 15}" font-size="11" fill="{ink}" text-anchor="middle">{b}</text></g>')
    ly = top + len(ROWS) * ch + 26
    o.append(f'<text x="24" y="{ly + 10}" font-size="11.5" fill="{MUTED}">{legend[0]}</text>')
    for k, c in enumerate(RAMP):
        o.append(f'<rect x="{left + k * 22}" y="{ly}" width="20" height="12" rx="2" fill="{c}"/>')
    o.append(f'<text x="{left + len(RAMP) * 22 + 8}" y="{ly + 10}" font-size="11.5" fill="{MUTED}">{legend[1]}</text>')
    o.append("</svg>")
    path.write_text("\n".join(o), encoding="utf-8", newline="\n")


def accuracy_lines(s):
    wrong = s["n"] - s["decoded"] - s["cut_off"] - s["declined"]
    notes = [
        f"{k} {what}"
        for k, what in ((wrong, "wrong"), (s["declined"], "gave no grid"), (s["cut_off"], "out of tokens"), (s["flipped"], "colour-flipped"))
        if k
    ]
    return f"{s['decoded']} of {s['n']}", "; ".join(notes) or "all exact"


heatmap(
    OUT / "accuracy.svg",
    "Images decoded pixel-for-pixel from text alone",
    "8×8 black-and-white images (a digit 7 and random noise), given as text with no tools. Formats run easiest to hardest.",
    ("none decoded", "all decoded"),
    lambda s: s["decoded"] / s["n"],
    accuracy_lines,
)
heatmap(
    OUT / "cost.svg",
    "Average cost of one call",
    "Same calls as the accuracy chart. Each cell also shows average reasoning tokens and time; reasoning is nearly all of the cost.",
    ("$0", f"{money(max_cost)} per call"),
    lambda s: s["cost"] / max_cost,
    lambda s: (money(s["cost"]), (f"{s['tokens'] / 1000:.1f}k tokens" if s["tokens"] else "no reasoning") + f", {s['seconds']:.0f} s"),
)

md = ["| Model | Effort | Format | Decoded | Avg. cost per call | Avg. reasoning tokens | Avg. time |", "|---|---|---|---|---|---|---|"]
for model, effort, name, note in ROWS:
    for fmt, fname in FORMATS:
        s = table.get((model, effort, fmt))
        if s:
            md.append(f"| {name} | {note} | {fname} | {s['decoded']} of {s['n']} | {money(s['cost'])} | {s['tokens']:,.0f} | {s['seconds']:.0f} s |")
(OUT / "table.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
print("\n".join(md))
