"""Stage 3-4: send prompts to a model through OpenRouter (plain chat, no tools).

The key is read from OPENROUTER_API_KEY, or from a .env file next to this
script containing a line  OPENROUTER_API_KEY=sk-or-...

Every reply is appended to responses.jsonl. A (model, prompt) pair already in
that file is skipped, so reruns never spend a request twice.

Examples:
  python run_openrouter.py --dry-run
  python run_openrouter.py --model google/gemma-4-31b-it:free --formats grid pgm
  python run_openrouter.py --size 8 --variant showwork --max 14
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
LOG = ROOT / "responses.jsonl"
URL = "https://openrouter.ai/api/v1/chat/completions"
FORMATS = ("grid", "pgm", "pbm", "bmp", "png")

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("--model", default="google/gemma-4-31b-it:free")
p.add_argument("--size", type=int, default=8, choices=(8, 16, 32))
p.add_argument("--variant", default="guided", choices=("blind", "guided", "showwork"))
p.add_argument("--formats", nargs="+", default=list(FORMATS), choices=FORMATS)
p.add_argument("--images", nargs="+", help="image names, e.g. digit_7 shape_x (default: all)")
p.add_argument("--max", type=int, default=10, help="hard cap on requests sent this run")
p.add_argument("--delay", type=float, default=4.0, help="seconds between requests (free tier: 20/min)")
p.add_argument("--max-tokens", type=int, default=4000)
p.add_argument("--dry-run", action="store_true", help="list what would be sent, send nothing")
args = p.parse_args()


def load_key():
    key = os.environ.get("OPENROUTER_API_KEY")
    env = ROOT / ".env"
    if not key and env.exists():
        for line in env.read_text().splitlines():
            if line.strip().startswith("OPENROUTER_API_KEY="):
                key = line.split("=", 1)[1].strip().strip("\"'")
    return key


done = set()
if LOG.exists():
    for line in LOG.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        done.add((r["model"], r["prompt_file"]))

todo = []
for fmt in args.formats:  # format-major order, so the easy rungs run first
    for path in sorted((ROOT / "prompts" / f"{args.size}x{args.size}").glob(f"*_{fmt}_{args.variant}.txt")):
        image = path.name[: -len(f"_{fmt}_{args.variant}.txt")]
        if args.images and image not in args.images:
            continue
        rel = path.relative_to(ROOT).as_posix()
        if (args.model, rel) not in done:
            todo.append((image, fmt, rel, path))

print(f"{len(todo)} prompts pending for {args.model}; sending at most {args.max}")
todo = todo[: args.max]
if args.dry_run:
    for _, _, rel, _ in todo:
        print("  would send", rel)
    raise SystemExit

key = load_key()
if not key:
    raise SystemExit("No key found: set OPENROUTER_API_KEY or put it in .env")

for i, (image, fmt, rel, path) in enumerate(todo):
    if i:
        time.sleep(args.delay)
    body = {
        "model": args.model,
        "messages": [{"role": "user", "content": path.read_text()}],
        "temperature": 0,
        "max_tokens": args.max_tokens,
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        # stop rather than retry: on a free key a 429 usually means the daily quota is gone
        raise SystemExit(f"HTTP {e.code} on {rel}: {e.read().decode(errors='replace')[:500]}")
    if "error" in data:
        raise SystemExit(f"API error on {rel}: {json.dumps(data['error'])[:500]}")

    choice = data["choices"][0]
    record = {
        "model": args.model,
        "prompt_file": rel,
        "image": image,
        "size": args.size,
        "format": fmt,
        "variant": args.variant,
        "response": choice["message"].get("content") or "",
        "reasoning": choice["message"].get("reasoning"),
        "finish_reason": choice.get("finish_reason"),
        "usage": data.get("usage"),
    }
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"[{i + 1}/{len(todo)}] {image} {fmt}: {record['response'].strip()[-200:]!r}")
