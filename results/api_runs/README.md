# API runs: interim results

**Status: interim.** 86 replies as of 5 October 2026, 11:15 IST. The GPT-6 Luna sweep is complete (75 calls). A retry of its cut-off PNG calls with a doubled token cap is running, and the Sonnet / Sol / Gemini comparison on more images has not started. Spend so far: **$0.33** of a $1.25 cap (the key holds $5).

## The question, and the short answer

**Question:** if a model is given only the base64 text of an image file, with no tools and no image input, can it work out what the picture is?

**Short answer so far:** yes for tiny images, but only when the model reasons, and how the file is stored decides how hard it is.

1. Claude Sonnet 5.5 and GPT-6 Sol each reconstructed every pixel of an 8×8 PNG through the API, where no code can run. One image and one run each so far.
2. With reasoning off, nothing decodes: GPT-6 Luna got 0 of 16 base64 images right, at coin-flip accuracy.
3. It is decoding, not guessing: Luna reproduced random-noise images exactly in the uncompressed formats.
4. Uncompressed formats are within reach of a small model; compressed PNG mostly is not.
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

Luna, the cheapest model, could not do the 8×8 PNGs at any effort within a 12,000-token cap (see the PNG row below), so PNG decoding depends on the model, not just on turning reasoning on.

Gemini used almost all of its 12,000-token cap, so the cap may have cut it short. In the earlier chat-UI run it thought for nearly six minutes and got it right.

### 3. Difficulty follows the file format (GPT-6 Luna, four images per cell, 8×8 unless stated)

Exact decodes out of 4:

| Format | No reasoning | Low | High | Avg. reasoning tokens at high |
|---|---|---|---|---|
| Text grid (control) | 4 / 4 | 4 / 4 | 4 / 4 | 883 |
| PBM (1 bit per pixel) | 0 / 4 | 2 / 4 | 4 / 4 | 1,727 |
| PGM (1 byte per pixel) | 0 / 4 | 0 / 4 | 4 / 4 | 7,192 |
| BMP | 0 / 4 | 4 / 4 | 2 / 4 | 8,519 |
| PNG | 0 / 4 | 0 / 4 | 0 / 4 | 12,000 (the cap) |
| PBM at 16×16 | not run | not run | 2 / 4 | 5,917 |
| PNG at 16×16 | not run | not run | 1 / 4 | 11,273 |

- The noise images decode as well as the shapes at high effort (PBM and PGM: 4 of 4 each), so this is decoding and not guessing.
- PGM costs about four times the reasoning of PBM for the same picture, because the file is five times longer. Length of the base64, not just the format's complexity, drives the effort.
- At low effort on PGM the model declined three times out of four, saying it could not decode reliably.
- 8×8 PNG was out of Luna's reach at a 12,000-token cap. At low effort it declined all four. At high effort it used the whole cap on reasoning and returned no answer, on all four images in each of three runs (12 of 12). This is "did not finish", not a wrong answer; the retry at 24,000 tokens tests whether more room helps.
- One PNG did decode: the 16×16 `noise_a`, all 256 pixels, in 9,094 reasoning tokens. The other three 16×16 PNGs were cut off. The likely reason is in the file: noise does not compress, so that PNG stores its pixel data uncompressed, while the others use Huffman coding (checked by reading the files). Not all PNGs are equally hard; the compression inside is what costs the reasoning.
- At 16×16 the PBM decodes held up: two exact, and the other two had 244 and 243 of 256 pixels right, one of them a noise image.
- BMP did better at low effort than at high (4 of 4 against 2 of 4). The two high-effort misses were small: 56 and 62 of 64 pixels. With four images per cell this may be noise.

### 4. Decoding the pixels is not the same as recognising the picture

- GPT-6 Luna decoded the BMP of the X exactly and then called it "a white diamond on a black background".
- GPT-6 Sol decoded the PNG exactly with colours flipped. PNG stores 0 as black and the prompt asks for 1 as black, so this is a prompt trap as much as a model error.

Decoding and interpretation should be scored separately.

### 5. Claude Sonnet 5.5 behaves differently when it does not reason

At low and medium effort Sonnet did no reasoning at all (zero reasoning tokens in four calls). Twice it refused to give a grid, saying it would be fabrication. Twice it gave a grid but labelled it a guess with low confidence. It never claimed a made-up answer with high confidence, unlike Luna and Gemini.

## Cost and time

| Model | Calls | Spend |
|---|---|---|
| GPT-6 Luna | 77 | $0.163 |
| Claude Sonnet 5.5 | 5 | $0.084 |
| Gemini 3.8 Flash | 2 | $0.047 |
| GPT-6 Sol | 2 | $0.037 |
| **Total** | **86** | **$0.331** |

- Cost is almost entirely reasoning tokens. A no-reasoning call costs a fraction of a cent on any model.
- Replies took 1–3 s without reasoning and 15–113 s with it. No call timed out or failed.
- 15 Luna calls ($0.09) were cut off at the token cap with no answer. They are billed all the same.

## Caveats

- Most cells have one run. Only the Luna 8×8 sweep has four images per cell.
- Pixel accuracy flatters sparse shapes: an all-white reply scores about 80% on a digit. The "exact" counts and the noise images are the numbers to trust.
- "No reasoning" is not available on Gemini 3.8 Flash or Claude Sonnet 5.5 through the API; their lowest setting is `low`, at which both happened to do no reasoning.
- The token cap also limits how long a model can think, so a failure near the cap (Gemini) is not a clean failure.

## Still to come

- Retry of the 15 cut-off Luna PNG calls with the token cap doubled to 24,000 (running; at most $0.18).
- Sonnet (low / high), Sol (none / medium) and Gemini (low only) on `digit_7` and `noise_a`, as PBM and PNG, plus one 16×16 noise image. Expected cost about $0.55.
