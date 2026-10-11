"""Stage 7: build the GitHub Pages site, docs/index.html.

Costs nothing: it reads results.csv, responses.jsonl and the image files, and
fills site_template.html with the numbers. Run score.py first.
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
IMAGES = ("digit_7", "noise_a")  # the two 8x8 images every model was given
FORMATS = ("grid", "pbm", "pgm", "bmp", "png")
# (model id, effort, name, effort label, vendor); only settings run on all five formats
CONFIGS = (
    ("anthropic/claude-sonnet-5.5", "high", "Claude Sonnet 5.5", "high effort", "anthropic"),
    ("openai/gpt-6-sol", "medium", "GPT-6 Sol", "medium effort", "openai"),
    ("openai/gpt-6-luna", "high", "GPT-6 Luna", "high effort", "openai"),
    ("openai/gpt-6-luna", "low", "GPT-6 Luna", "low effort", "openai"),
    ("google/gemini-3.8-flash", "low", "Gemini 3.8 Flash", "low effort", "google"),
    ("openai/gpt-6-luna", "none", "GPT-6 Luna", "reasoning off", "openai"),
)
# replies to the PNG of the 7, in the order the gallery shows them:
# (model id, effort, run, name, setting, what the model said it was, verdict)
GALLERY = (
    ("anthropic/claude-sonnet-5.5", "high", 1, "Claude Sonnet 5.5", "high effort", "“The digit 7.” Confidence: medium–high.", "decoded"),
    ("openai/gpt-6-sol", "medium", 1, "GPT-6 Sol", "medium effort", "“A white 7 on a black background.” Confidence: high.", "flipped"),
    ("openai/gpt-6-luna", "high", 2, "GPT-6 Luna", "high effort, 2nd run", "“The digit 7.” Confidence: high.", "decoded"),
    ("openai/gpt-6-luna", "high", 3, "GPT-6 Luna", "high effort, 3rd run", "“A short horizontal bar with a narrow, slightly zigzagging stem.” Confidence: medium.", "decoded"),
    ("google/gemini-3.8-flash", "medium", 1, "Gemini 3.8 Flash", "medium effort", "“An X, formed by two intersecting diagonal lines.” Confidence: high.", "wrong"),
    ("google/gemini-3.8-flash", "low", 1, "Gemini 3.8 Flash", "low effort", "“A classic pixel-art smiley face.” Confidence: high.", "wrong"),
    ("openai/gpt-6-luna", "none", 1, "GPT-6 Luna", "reasoning off", "“A small pixel-art key.” Confidence: medium.", "wrong"),
    ("openai/gpt-6-luna", "medium", 1, "GPT-6 Luna", "medium effort", "“An abstract pixel pattern; I can’t confidently identify it.” Confidence: low.", "wrong"),
    ("anthropic/claude-sonnet-5.5", "medium", 2, "Claude Sonnet 5.5", "medium effort, did not reason", "“This guess looks like the letter A … not a verified decode.” Confidence: low.", "guess"),
    ("anthropic/claude-sonnet-5.5", "low", 1, "Claude Sonnet 5.5", "low effort, did not reason", "“A made-up grid would be fabricated, so I’m not giving one.”", "declined"),
)


def find_grid(text, n):
    rows = [re.sub(r"[\s`|]", "", line) for line in text.splitlines()]
    ok = [bool(re.fullmatch(f"[01]{{{n}}}", r)) for r in rows]
    for end in range(len(rows), n - 1, -1):
        if all(ok[end - n : end]):
            return rows[end - n : end]
    return None


truth = {(im["name"], im["size"]): im["grid"] for im in json.loads((ROOT / "images" / "images.json").read_text())}
encodings = {(e["name"], e["size"]): e for e in json.loads((ROOT / "encodings.json").read_text())}

cells = defaultdict(list)
for r in csv.DictReader(open(ROOT / "results.csv")):
    if r["size"] == "8" and r["image"] in IMAGES:
        cells[r["model"], r["effort"], r["format"]].append(r)

configs = []
for model, effort, name, label, vendor in CONFIGS:
    per_format = {}
    for fmt in FORMATS:
        rows = cells[model, effort, fmt]
        n = len(rows)
        flipped = sum(r["pixel_acc_inverted"] == "1.0" for r in rows)
        decoded = sum(r["exact"] == "1" for r in rows) + flipped
        cut_off = sum(r["finish_reason"] == "length" and r["pixel_acc"] == "" for r in rows)
        declined = sum(r["finish_reason"] != "length" and r["pixel_acc"] == "" for r in rows)
        per_format[fmt] = {
            "n": n,
            "decoded": decoded,
            "flipped": flipped,
            "cutOff": cut_off,
            "declined": declined,
            "wrong": n - decoded - cut_off - declined,
            "cost": sum(float(r["cost"]) for r in rows) / n,
            "tokens": sum(int(r["reasoning_tokens"] or 0) for r in rows) / n,
            "seconds": sum(float(r["seconds"]) for r in rows) / n,
        }
    configs.append({"name": name, "effort": label, "vendor": vendor, "formats": per_format})

latest = {}
for line in (ROOT / "responses.jsonl").read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    if "error" not in r and r["image"] == "digit_7" and r["size"] == 8 and r["format"] == "png":
        if r["response"].strip():
            latest[r["model"], r["effort"], r["run"]] = r
gallery = []
for model, effort, run, name, setting, said, verdict in GALLERY:
    r = latest[model, effort, run]
    gallery.append(
        {
            "name": name,
            "setting": setting,
            "said": said,
            "verdict": verdict,
            "grid": find_grid(r["response"], 8),
            "tokens": r["reasoning_tokens"] or 0,
            "seconds": r["seconds"],
            "cost": r["cost"],
        }
    )

ok = [json.loads(l) for l in (ROOT / "responses.jsonl").read_text(encoding="utf-8").splitlines()]
ok = [r for r in ok if "error" not in r]
spend = defaultdict(lambda: [0, 0.0])
for r in ok:
    spend[r["model"]][0] += 1
    spend[r["model"]][1] += r["cost"]

seven = encodings["digit_7", 8]
data = {
    "configs": configs,
    "formats": list(FORMATS),
    "gallery": gallery,
    "truth": {name: truth[name, 8] for name in ("digit_7", "shape_x", "noise_a", "noise_b")},
    "encodings": {fmt: seven[fmt] for fmt in FORMATS},
    "spend": [{"model": m, "calls": c, "cost": v} for m, (c, v) in sorted(spend.items(), key=lambda kv: -kv[1][1])],
    "totalCalls": len(ok),
    "totalCost": sum(r["cost"] for r in ok),
}

html = (ROOT / "site_template.html").read_text(encoding="utf-8").replace("__DATA__", json.dumps(data, ensure_ascii=False))
out = ROOT / "docs"
out.mkdir(exist_ok=True)
(out / "index.html").write_text(html, encoding="utf-8", newline="\n")
(out / ".nojekyll").write_text("", newline="\n")
print(f"wrote docs/index.html ({len(html):,} characters), {len(ok)} replies, ${data['totalCost']:.2f}")
