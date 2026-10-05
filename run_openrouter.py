"""Stages 3-4: send the show-work prompts to models through OpenRouter.

Plain text in, text out: no tools are passed, so a model cannot run a decoder.

The key is read from OPENROUTER_API_KEY, or from a .env file next to this
script containing a line  OPENROUTER_API_KEY=sk-or-...

Every request and its full reply are appended to responses.jsonl. A call is
identified by (model, prompt text, reasoning effort, run number); one already
in that file is never sent again. Spend is added up from the cost OpenRouter
reports, and the script stops before any call that could cross a budget.

Examples:
  python run_openrouter.py --check-key
  python run_openrouter.py --phase 1 --dry-run
  python run_openrouter.py --phase 1
  python run_openrouter.py --model anthropic/claude-opus-5.5 --images digit_7 \\
      --formats png --efforts medium --dry-run
"""
import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from collections import namedtuple
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
LOG = ROOT / "responses.jsonl"
API = "https://openrouter.ai/api/v1"
FORMATS = ("grid", "pgm", "pbm", "bmp", "png")
VARIANT = "showwork"  # the only variant that yields a pixel grid to score

LUNA = "openai/gpt-6-luna"
SOL = "openai/gpt-6-sol"
GEMINI = "google/gemini-3.8-flash"
SONNET = "anthropic/claude-sonnet-5.5"
OPUS = "anthropic/claude-opus-5.5"

# Prices in $ per 1M tokens (OpenRouter, 2026-10-05). `cap` is max_tokens for a
# reasoning call; reasoning is billed as output, so cap x price_out bounds a call.
# `floor` is the lowest reasoning effort the model accepts: Gemini and Claude
# cannot switch reasoning off.
MODELS = {
    LUNA: dict(price_in=0.10, price_out=0.50, cap=12000, floor="none"),
    GEMINI: dict(price_in=0.75, price_out=3.75, cap=12000, floor="low"),
    SONNET: dict(price_in=2.00, price_out=10.00, cap=8000, floor="low"),
    SOL: dict(price_in=2.00, price_out=10.00, cap=8000, floor="none"),
    OPUS: dict(price_in=4.00, price_out=20.00, cap=8000, floor="low"),
}
TOTAL_BUDGET = 1.25
PHASE_BUDGET = {"1": 0.30, "2": 0.25, "3": 0.70}

Call = namedtuple("Call", "phase model image size fmt effort run")


def plan(phase):
    calls = []
    add = lambda *a: calls.append(Call(phase, *a))
    if phase == "1":
        # pilot: the hand-run prompt on every model, lowest effort vs medium
        for m in (LUNA, GEMINI, SONNET, SOL):
            for effort in (MODELS[m]["floor"], "medium"):
                add(m, "digit_7", 8, "png", effort, 1)
    elif phase == "2":
        # cheap model, full sweep: every format, three effort levels
        images = ("digit_7", "shape_x", "noise_a", "noise_b")
        for fmt in FORMATS:  # format-major order, so the easy rungs run first
            for image in images:
                for effort in ("none", "low", "high"):
                    add(LUNA, image, 8, fmt, effort, 1)
        for fmt in ("pbm", "png"):
            for image in images:
                add(LUNA, image, 16, fmt, "high", 1)
        for run in (2, 3):
            for image in images:
                add(LUNA, image, 8, "png", "high", run)
    elif phase == "3":
        # pricier models on the key cells only; cell-major order, so a budget
        # stop costs every model the same tail. Arms come from the pilot: Sonnet
        # does not reason below high, and Gemini at medium spends its whole cap.
        arms = {GEMINI: ("low",), SONNET: ("low", "high"), SOL: ("none", "medium")}
        for size, image, fmt, models in (
            (8, "noise_a", "png", (GEMINI, SONNET, SOL)),
            (8, "noise_a", "pbm", (GEMINI, SONNET, SOL)),
            (8, "digit_7", "png", (GEMINI, SONNET, SOL)),
            (8, "digit_7", "pbm", (GEMINI, SONNET, SOL)),
            (16, "noise_a", "png", (GEMINI, SONNET, SOL)),
            (16, "noise_a", "pbm", (GEMINI,)),
        ):
            for m in models:
                for effort in arms[m][-1:] if size == 16 else arms[m]:
                    add(m, image, size, fmt, effort, 1)
    return calls


def max_tokens(c):
    cap = MODELS[c.model]["cap"]
    return 2000 if c.effort == "none" else cap // 2 if c.effort == "low" else cap


def prompt_path(c):
    return ROOT / "prompts" / f"{c.size}x{c.size}" / f"{c.image}_{c.fmt}_{VARIANT}.txt"


def cache_key(c, text):
    return (c.model, hashlib.sha256(text.encode()).hexdigest(), c.effort, c.run)


def worst_cost(c, text):
    m = MODELS[c.model]
    # base64 tokenises badly: assume 2 characters per token
    return (len(text) / 2 * m["price_in"] + max_tokens(c) * m["price_out"]) / 1e6


def load_key():
    key = os.environ.get("OPENROUTER_API_KEY")
    env = ROOT / ".env"
    if not key and env.exists():
        for line in env.read_text().splitlines():
            if line.strip().startswith("OPENROUTER_API_KEY="):
                key = line.split("=", 1)[1].strip().strip("\"'")
    if not key:
        raise SystemExit("No key found: set OPENROUTER_API_KEY or put it in .env")
    return key


def check_key(key):
    req = urllib.request.Request(f"{API}/key", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        info = json.load(resp)["data"]
    for field in ("label", "limit", "usage", "limit_remaining", "limit_reset", "expires_at", "is_free_tier"):
        if field in info:
            print(f"  {field}: {info[field]}")
    return info


def append(record):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("--phase", choices=sorted(PHASE_BUDGET), help="run a planned phase")
p.add_argument("--model", choices=sorted(MODELS), help="ad-hoc run: one model, cells from the flags below")
p.add_argument("--images", nargs="+", default=["digit_7"])
p.add_argument("--sizes", nargs="+", type=int, default=[8], choices=(8, 16, 32))
p.add_argument("--formats", nargs="+", default=["png"], choices=FORMATS)
p.add_argument("--efforts", nargs="+", default=["medium"], choices=("none", "low", "medium", "high"))
p.add_argument("--runs", type=int, default=1, help="ad-hoc run: repeats per cell")
p.add_argument("--budget", type=float, default=TOTAL_BUDGET, help="total $ across everything in responses.jsonl")
p.add_argument("--max", type=int, help="hard cap on requests sent this run")
p.add_argument("--dry-run", action="store_true", help="list what would be sent and its worst-case cost, send nothing")
p.add_argument("--check-key", action="store_true", help="show the key's limit and usage, send nothing")
args = p.parse_args()

if args.check_key:
    check_key(load_key())
    raise SystemExit
if bool(args.phase) == bool(args.model):
    p.error("give exactly one of --phase or --model")

if args.phase:
    calls = plan(args.phase)
else:
    calls = [
        Call("adhoc", args.model, image, size, fmt, effort, run)
        for size in args.sizes
        for fmt in args.formats
        for image in args.images
        for effort in args.efforts
        for run in range(1, args.runs + 1)
    ]

done, spent, phase_spent = set(), 0.0, 0.0
if LOG.exists():
    for line in LOG.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if "error" in r:
            continue
        done.add((r["model"], r["prompt_sha256"], r["effort"], r["run"]))
        spent += r["cost"]
        if r["phase"] == args.phase:
            phase_spent += r["cost"]

todo = []
for c in calls:
    text = prompt_path(c).read_text(encoding="utf-8")
    if cache_key(c, text) not in done:
        done.add(cache_key(c, text))
        todo.append((c, text))
todo = todo[: args.max]
phase_budget = PHASE_BUDGET.get(args.phase, args.budget)

print(f"{len(calls)} calls planned, {len(calls) - len(todo)} cached or cut by --max, {len(todo)} to send")
print(f"spent so far ${spent:.4f} of ${args.budget:.2f}; this phase ${phase_spent:.4f} of ${phase_budget:.2f}")
if args.dry_run:
    per_model = {}
    for c, text in todo:
        w = worst_cost(c, text)
        n, total = per_model.get(c.model, (0, 0.0))
        per_model[c.model] = (n + 1, total + w)
        print(f"  {c.model:28} {c.image:8} {c.size:>2} {c.fmt:4} effort={c.effort:6} run={c.run}  worst ${w:.4f}")
    for model, (n, total) in per_model.items():
        print(f"{model}: {n} calls, worst case ${total:.4f}")
    print(f"worst case for this run: ${sum(t for _, t in per_model.values()):.4f}")
    raise SystemExit

key = load_key()
try:
    check_key(key)
except Exception as e:  # informational only
    print(f"  (key check failed: {e})")

for i, (c, text) in enumerate(todo):
    worst = worst_cost(c, text)
    if spent + worst > args.budget:
        raise SystemExit(f"Stopping: total budget ${args.budget:.2f} could be crossed (spent ${spent:.4f})")
    if phase_spent + worst > phase_budget:
        raise SystemExit(f"Stopping: phase budget ${phase_budget:.2f} could be crossed (spent ${phase_spent:.4f})")

    body = {
        "model": c.model,
        "messages": [{"role": "user", "content": text}],
        "max_tokens": max_tokens(c),
        "reasoning": {"effort": c.effort},
        "usage": {"include": True},
    }
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "phase": c.phase,
        "model": c.model,
        "image": c.image,
        "size": c.size,
        "format": c.fmt,
        "variant": VARIANT,
        "effort": c.effort,
        "run": c.run,
        "prompt_file": prompt_path(c).relative_to(ROOT).as_posix(),
        "prompt_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "request": body,
    }
    req = urllib.request.Request(
        f"{API}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        # stop rather than retry: a rejected request costs nothing, a retry loop might
        record["error"] = f"HTTP {e.code}: {e.read().decode(errors='replace')[:2000]}"
        append(record)
        raise SystemExit(f"{record['error'][:500]}\non {record['prompt_file']} ({c.model}, effort={c.effort})")
    except Exception as e:
        record["error"] = f"{type(e).__name__}: {e}"
        append(record)
        raise SystemExit(
            f"{record['error']}\nThe request may still have been billed: check openrouter.ai/activity before rerunning."
        )
    record["seconds"] = round(time.perf_counter() - start, 1)
    if "error" in data or not data.get("choices"):
        record["error"] = json.dumps(data)[:2000]
        append(record)
        raise SystemExit(f"API error on {record['prompt_file']}: {record['error'][:500]}")

    choice = data["choices"][0]
    usage = data.get("usage") or {}
    cost = usage.get("cost")
    if cost is None:  # fall back to list prices
        m = MODELS[c.model]
        cost = (usage.get("prompt_tokens", 0) * m["price_in"] + usage.get("completion_tokens", 0) * m["price_out"]) / 1e6
        record["cost_estimated"] = True
    record.update(
        response=choice["message"].get("content") or "",
        reasoning=choice["message"].get("reasoning"),
        finish_reason=choice.get("finish_reason"),
        reasoning_tokens=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
        usage=usage,
        cost=cost,
        raw=data,
    )
    append(record)
    spent += cost
    phase_spent += cost

    note = "" if record["response"].strip() else "  ** EMPTY REPLY (hit the token cap?) **"
    print(
        f"[{i + 1}/{len(todo)}] {c.model} {c.image} {c.size} {c.fmt} effort={c.effort} run={c.run}: "
        f"{record['seconds']}s, {usage.get('completion_tokens')} out tokens "
        f"({record['reasoning_tokens']} reasoning), ${cost:.4f}, finish={record['finish_reason']}{note}"
    )
    print(f"    {ascii(record['response'].strip()[-160:])}")

print(f"done. spent ${spent:.4f} of ${args.budget:.2f} in total")
