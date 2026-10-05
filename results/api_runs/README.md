# API runs: interim results

**Status: interim.** 101 replies as of 5 October 2026, 12:25 IST. The GPT-6 Luna sweep is complete, including a retry of its 15 cut-off PNG calls with a doubled token cap. The Sonnet / Sol / Gemini comparison on more images has not started. Spend so far: **$0.48** of a $1.25 cap (the key holds $5).

## The question, and the short answer

**Question:** if a model is given only the base64 text of an image file, with no tools and no image input, can it work out what the picture is?

**Short answer so far:** yes for tiny images, but only when the model reasons, and how the file is stored decides how hard it is.

1. Claude Sonnet 5.5 and GPT-6 Sol each reconstructed every pixel of an 8×8 PNG through the API, where no code can run. One image and one run each so far.
2. With reasoning off, nothing decodes: GPT-6 Luna got 0 of 16 base64 images right, at coin-flip accuracy.
3. It is decoding, not guessing: Luna reproduced random-noise images exactly in the uncompressed formats.
4. Uncompressed formats are within reach of a small model. Compressed PNG is at the edge of it: Luna got some, including one compressed noise image, but only with a very large reasoning allowance and not reliably.
5. Models that do not reason often state wrong answers with high confidence. Sonnet did not.

**What this is not.** It is not advice on how to send images to a model. Attaching an image normally uses the model's vision input, which is far cheaper and more reliable than any of this. It also does not show that BMP saves tokens: BMP's base64 is longer than PNG's (128 characters against 100–108 for these 8×8 images). The experiment measures how far text-only reasoning goes on raw file bytes.

## Setup

Each model gets one text prompt through the OpenRouter API and returns text. No tools are passed, so it cannot run a decoder: whatever it gets right, it worked out in its reasoning. This closes the gap in the earlier chat-UI runs, where the chatbot could have used code.

- **Prompt:** the show-work variant. The model writes out the pixel grid (1 = black), then names the image and its confidence.
- **Images:** `digit_7`, `shape_x`, and two random-noise images. Noise has no shape to guess, so only real decoding scores on it; chance is 50%.
- **Reasoning effort** is the main variable, from none up to high.
- **Scoring:** the grid in the reply is compared with the true pixels. "Exact" means all 64 pixels right.

Every request and reply is in [responses.jsonl](../../responses.jsonl); per-reply scores are in [results.csv](../../results.csv).

## Findings so far

### 1. Without reasoning, models cannot decode, and they often say they can

With reasoning off, GPT-6 Luna got 0 of 16 base64 images right. Where it gave a grid, pixel accuracy sat at 38–67%, which is around chance. In 6 of those 16 it still stated high confidence.

Gemini 3.8 Flash at its lowest setting did no reasoning and described a "smiley face" with high confidence. The image was a 7.

### 2. With reasoning, decoding is real, including PNG

| Model | Effort | Reasoning tokens | Time | Cost | Result on `digit_7` 8×8 PNG |
|---|---|---|---|---|---|
| Claude Sonnet 5.5 | high | 6,327 | 49 s | $0.066 | All 64 pixels right, named "7" |
| GPT-6 Sol | medium | 3,537 | 35 s | $0.036 | All 64 pixels right but colours inverted; still named "a white 7 on a black background" |
| Gemini 3.8 Flash | medium | 11,520 | 69 s | $0.045 | Wrong: a tidy but invented decode of an "X", high confidence |
| GPT-6 Luna | medium | 8,054 | 74 s | $0.004 | Wrong: first two rows nearly right, then lost; low confidence |

Two models decompressed a PNG in their reasoning with no tools. This is one image and one run each, so it needs the repeats and the noise images before it is a firm claim.

Luna, the cheapest model, needed far more than that. It decoded none of the 8×8 PNGs within 12,000 tokens and only some within 24,000 (see finding 3), so PNG decoding depends on the model, not just on turning reasoning on.

Gemini used almost all of its 12,000-token cap, so the cap may have cut it short. In the earlier chat-UI run it thought for nearly six minutes and got it right.

### 3. Difficulty follows the file format (GPT-6 Luna, four images per cell, 8×8 unless stated)

Exact decodes out of 4:

| Format | No reasoning | Low | High | Avg. reasoning tokens at high |
|---|---|---|---|---|
| Text grid (control) | 4 / 4 | 4 / 4 | 4 / 4 | 883 |
| PBM (1 bit per pixel) | 0 / 4 | 2 / 4 | 4 / 4 | 1,727 |
| PGM (1 byte per pixel) | 0 / 4 | 0 / 4 | 4 / 4 | 7,192 |
| BMP | 0 / 4 | 4 / 4 | 2 / 4 | 8,519 |
| PNG | 0 / 4 | 0 / 4 | see below | |
| PBM at 16×16 | not run | not run | 2 / 4 | 5,917 |

- The noise images decode as well as the shapes at high effort (PBM and PGM: 4 of 4 each), so this is decoding and not guessing.
- PGM costs about four times the reasoning of PBM for the same picture, because the file is five times longer. Length of the base64, not just the format's complexity, drives the effort.
- At low effort on PGM the model declined three times out of four, saying it could not decode reliably.
- At 16×16 the PBM decodes held up: two exact, and the other two had 244 and 243 of 256 pixels right, one of them a noise image.
- BMP did better at low effort than at high (4 of 4 against 2 of 4). The two high-effort misses were small: 56 and 62 of 64 pixels. With four images per cell this may be noise.

### 4. PNG at high effort: Luna needs a very large reasoning allowance, and the compression inside the file decides the outcome

With a 12,000-token cap, 15 of 16 PNG calls spent the whole cap on reasoning and returned no answer. Those were resent with a 24,000-token cap. Results at high effort, best cap per call:

| Image | Size | Compression inside the PNG | Result |
|---|---|---|---|
| `digit_7` | 8×8 | Fixed Huffman | Run 1 cut off at 24,000; runs 2 and 3 exact (21,188 and 12,638 reasoning tokens) |
| `shape_x` | 8×8 | Fixed Huffman | Runs 1 and 3 exact (13,984 and 14,955); run 2 cut off at 24,000 |
| `noise_a` | 8×8 | Fixed Huffman | Runs 1 and 2 cut off at 24,000; run 3 exact (17,173) |
| `noise_b` | 8×8 | Fixed Huffman | All three runs cut off at 24,000 |
| `shape_x` | 16×16 | None (stored) | Exact, all 256 pixels (11,683) |
| `noise_a` | 16×16 | None (stored) | Exact, all 256 pixels (9,094, at the 12,000 cap) |
| `noise_b` | 16×16 | Fixed Huffman | Cut off at 24,000 |
| `digit_7` | 16×16 | Dynamic Huffman | Answered after 22,790 tokens: said it could not decode and would not invent a grid |

- **Doubling the cap helped only partly.** Of the 15 retried calls, 6 came back exact, 1 declined, and 8 were cut off again at 24,000 tokens. At 8×8 that is 5 exact out of 12.
- **Every grid Luna did give was exactly right.** At high effort on PNG it produced seven grids, all perfect, and never a wrong one. It either finishes correctly, declines, or runs out.
- **The compression inside the PNG matters more than the image size.** Both PNGs whose pixel data is stored uncompressed were decoded, though they are 16×16. The compression type was read from the files; that it explains the pattern is an inference from eight images.
- **The same call can succeed or fail between runs.** `digit_7` 8×8 was cut off once and exact twice; `shape_x` 8×8 was exact once and cut off once.
- **One compressed noise PNG decoded exactly:** `noise_a` 8×8 on its third run, all 64 pixels. Random pixels cannot be guessed, so this is real decompression by the cheapest model. It is one success in six attempts on compressed noise PNGs.
- One retried `digit_7` was pixel-exact but described as "a short horizontal bar with a zigzagging stem", not as a 7.

### 5. Decoding the pixels is not the same as recognising the picture

- GPT-6 Luna decoded the BMP of the X exactly and then called it "a white diamond on a black background".
- GPT-6 Sol decoded the PNG exactly with colours flipped. PNG stores 0 as black and the prompt asks for 1 as black, so this is a prompt trap as much as a model error.

Decoding and interpretation should be scored separately.

### 6. Claude Sonnet 5.5 behaves differently when it does not reason

At low and medium effort Sonnet did no reasoning at all (zero reasoning tokens in four calls). Twice it refused to give a grid, saying it would be fabrication. Twice it gave a grid but labelled it a guess with low confidence. It never claimed a made-up answer with high confidence, unlike Luna and Gemini.

## Cost and time

| Model | Calls | Spend |
|---|---|---|
| GPT-6 Luna | 92 | $0.316 |
| Claude Sonnet 5.5 | 5 | $0.084 |
| Gemini 3.8 Flash | 2 | $0.047 |
| GPT-6 Sol | 2 | $0.037 |
| **Total** | **101** | **$0.484** |

- Cost is almost entirely reasoning tokens. A no-reasoning call costs a fraction of a cent on any model.
- Replies took 1–3 s without reasoning and 15–113 s with it at a 12,000-token cap. At 24,000 tokens Luna's PNG calls took 2–4.5 minutes each.
- 23 Luna calls were cut off at a token cap with no answer. They are billed all the same and cost $0.19, more than a third of the spend so far.
- One call timed out: Luna on `shape_x` 8×8 PNG, third run, at the 24,000 cap. The runner stopped there and logged it, and the call was resent successfully. Whether the timed-out attempt was billed is unknown: OpenRouter's usage figure lags the log, so the two cannot be compared yet.

## Caveats

- Most cells have one run. Only the Luna 8×8 sweep has four images per cell.
- Pixel accuracy flatters sparse shapes: an all-white reply scores about 80% on a digit. The "exact" counts and the noise images are the numbers to trust.
- "No reasoning" is not available on Gemini 3.8 Flash or Claude Sonnet 5.5 through the API; their lowest setting is `low`, at which both happened to do no reasoning.
- The token cap also limits how long a model can think, so a failure near the cap (Gemini) is not a clean failure.

## Still to come

- Sonnet (low / high), Sol (none / medium) and Gemini (low only) on `digit_7` and `noise_a`, as PBM and PNG, plus one 16×16 noise image. Expected cost about $0.55.
