# API runs: results

**Status:** all planned runs are done. 128 replies from four models, 5–11 October 2026. Total spend: **$0.97** of a $1.25 cap.

## The question, and the answer

**Question:** if a model is given only the text of an image file (base64), with no tools and no image input, can it work out what the picture is?

**Answer:** yes, for tiny images, when the model reasons. Claude Sonnet 5.5 and GPT-6 Sol decoded every image in every format, including a compressed PNG of random noise, which cannot be guessed.

![Share of images decoded exactly, by model and format](accuracy.svg)

![Average cost of one call, by model and format](cost.svg)

How to read the charts:

- **Rows** are models, each at the reasoning effort where it works, plus GPT-6 Luna with reasoning off as a baseline.
- **Columns** are ways of storing the same picture, easiest to hardest. The text grid is the picture typed out as 0s and 1s (a sanity check). PBM, PGM and BMP list the pixels uncompressed. PNG compresses them, so the model has to decompress in its reasoning.
- **Two images** per cell: a digit 7 and an 8×8 block of random noise. GPT-6 Luna's PNG cell has three runs of each.
- **"Decoded"** means every one of the 64 pixels is right.

## Main findings

1. **The two stronger models decoded everything.** Sonnet 5.5 (high effort) and GPT-6 Sol (medium) each got 10 of 10, noise images included. No tools were available, so this is reasoning alone.
2. **Without reasoning, nothing decodes.** GPT-6 Luna with reasoning off got the text grid and nothing else, and often stated high confidence anyway.
3. **PNG is the expensive format.** For Sonnet and Sol a PNG costs 6–7 cents and about a minute, against under a cent and a few seconds for PBM. The picture is the same; decompressing is what costs.
4. **The cheap model reaches PNG only sometimes.** GPT-6 Luna decoded 3 of 6 PNG attempts and ran out of its 24,000-token allowance on the rest, taking over three minutes a call.
5. **Gemini 3.8 Flash at low effort is unreliable past the simplest format.** It got PBM right and failed PGM and PNG, twice giving a wrong picture with high confidence.

**What this is not.** It is not advice on how to send images to a model. Attaching an image normally uses the model's vision input, which is far cheaper and more reliable. The experiment measures how far text-only reasoning goes on raw file bytes.

## The numbers

| Model | Effort | Format | Decoded | Avg. cost per call | Avg. reasoning tokens | Avg. time |
|---|---|---|---|---|---|---|
| Claude Sonnet 5.5 | high effort | Text grid | 2 of 2 | $0.003 | 0 | 4 s |
| Claude Sonnet 5.5 | high effort | PBM | 2 of 2 | $0.008 | 598 | 7 s |
| Claude Sonnet 5.5 | high effort | PGM | 2 of 2 | $0.035 | 3,200 | 23 s |
| Claude Sonnet 5.5 | high effort | BMP | 2 of 2 | $0.020 | 1,704 | 15 s |
| Claude Sonnet 5.5 | high effort | PNG | 2 of 2 | $0.069 | 6,560 | 50 s |
| GPT-6 Sol | medium effort | Text grid | 2 of 2 | $0.002 | 143 | 4 s |
| GPT-6 Sol | medium effort | PBM | 2 of 2 | $0.005 | 465 | 6 s |
| GPT-6 Sol | medium effort | PGM | 2 of 2 | $0.017 | 1,628 | 15 s |
| GPT-6 Sol | medium effort | BMP | 2 of 2 | $0.013 | 1,228 | 13 s |
| GPT-6 Sol | medium effort | PNG | 2 of 2 | $0.063 | 6,170 | 58 s |
| GPT-6 Luna | high effort | Text grid | 2 of 2 | $0.001 | 1,036 | 13 s |
| GPT-6 Luna | high effort | PBM | 2 of 2 | $0.001 | 1,568 | 16 s |
| GPT-6 Luna | high effort | PGM | 2 of 2 | $0.004 | 8,434 | 68 s |
| GPT-6 Luna | high effort | BMP | 1 of 2 | $0.005 | 9,940 | 99 s |
| GPT-6 Luna | high effort | PNG | 3 of 6 | $0.010 | 20,500 | 196 s |
| Gemini 3.8 Flash | low effort | Text grid | 2 of 2 | $0.001 | 142 | 3 s |
| Gemini 3.8 Flash | low effort | PBM | 2 of 2 | $0.009 | 2,128 | 14 s |
| Gemini 3.8 Flash | low effort | PGM | 0 of 2 | $0.015 | 3,805 | 20 s |
| Gemini 3.8 Flash | low effort | BMP | 1 of 2 | $0.019 | 4,936 | 28 s |
| Gemini 3.8 Flash | low effort | PNG | 0 of 2 | $0.012 | 2,880 | 20 s |
| GPT-6 Luna | reasoning off | Text grid | 2 of 2 | under $0.001 | 0 | 2 s |
| GPT-6 Luna | reasoning off | PBM | 0 of 2 | under $0.001 | 0 | 2 s |
| GPT-6 Luna | reasoning off | PGM | 0 of 2 | under $0.001 | 0 | 1 s |
| GPT-6 Luna | reasoning off | BMP | 0 of 2 | under $0.001 | 0 | 2 s |
| GPT-6 Luna | reasoning off | PNG | 0 of 2 | under $0.001 | 0 | 2 s |

Costs are per call, averaged over the calls in the cell. Luna's PNG figure counts only the final attempt at each call; its earlier attempts that were cut off at a smaller token cap are in the spend table below.

## Setup

Each model gets one text prompt through the OpenRouter API and returns text. No tools are passed, so it cannot run a decoder. This closes the gap in the earlier chat-UI runs, where the chatbot could have used code.

- **Prompt:** the model writes out the pixel grid (1 = black), then names the image and its confidence.
- **Images:** `digit_7`, `shape_x`, and two random-noise images. Noise has no shape to guess; chance is 50% per pixel.
- **Reasoning effort** is set per call. Sonnet 5.5 and Gemini 3.8 Flash cannot switch reasoning off through the API.
- **Scoring:** the grid in the reply is compared with the true pixels. A grid that is exact with black and white swapped counts as decoded.

Every request and reply is in [responses.jsonl](../../responses.jsonl); per-reply scores are in [results.csv](../../results.csv). The charts and table are rebuilt by `make_table.py`.

## Findings in detail

### 1. Sonnet 5.5 and GPT-6 Sol: 10 of 10 each

- Both decoded the PNG of random noise exactly. Sol needed 8,804 reasoning tokens and 82 s for it; Sonnet 6,794 tokens and 50 s.
- Sol is the cheaper of the two on every format, at about half Sonnet's cost on the uncompressed ones. On PNG they cost about the same.
- Sol decoded the PNG of the 7 with black and white swapped, and still named it "a white 7 on a black background". PNG stores 0 as black and the prompt asks for 1 as black, so this is a prompt trap as much as a model error. On the noise PNG it got the colours right.
- One run per cell, two images per format.

### 2. Sonnet needs high effort; below that it does not reason

At low and medium effort Sonnet did no reasoning at all on the PNG (zero reasoning tokens in four calls). Twice it refused to give a grid, saying it would be fabrication. Twice it gave a grid but labelled it a guess with low confidence. It never claimed a made-up answer with high confidence.

### 3. Gemini 3.8 Flash

- **At low effort** it reasoned on some calls and not others (0 to 5,761 reasoning tokens). It decoded PBM twice and the BMP of the 7. It got PGM and PNG wrong, and on two calls ran out of its 6,000-token cap.
- **Wrong answers came with high confidence:** a "smiley face" for the PNG of the 7, and a grid at chance accuracy for the noise PNG.
- **At medium effort** (one call, the PNG of the 7) it used its whole 12,000-token cap and gave an invented decode of an "X", again with high confidence. Medium was not run further because of cost.
- In the earlier chat-UI run, Gemini with extended thinking took nearly six minutes and got this image right, so the caps here may be what holds it back.

### 4. The cheap model in detail (GPT-6 Luna, four images per cell, 8×8 unless stated)

Exact decodes out of 4:

| Format | No reasoning | Low | High | Avg. reasoning tokens at high |
|---|---|---|---|---|
| Text grid (control) | 4 / 4 | 4 / 4 | 4 / 4 | 883 |
| PBM (1 bit per pixel) | 0 / 4 | 2 / 4 | 4 / 4 | 1,727 |
| PGM (1 byte per pixel) | 0 / 4 | 0 / 4 | 4 / 4 | 7,192 |
| BMP | 0 / 4 | 4 / 4 | 2 / 4 | 8,519 |
| PNG | 0 / 4 | 0 / 4 | 5 / 12 over three runs (finding 5) | 20,661 |
| PBM at 16×16 | not run | not run | 2 / 4 | 5,917 |

- The noise images decode as well as the shapes at high effort (PBM and PGM: 4 of 4 each), so this is decoding and not guessing.
- PGM costs about four times the reasoning of PBM for the same picture, because the file is five times longer. Length of the base64, not just the format's complexity, drives the effort.
- At low effort on PGM the model declined three times out of four, saying it could not decode reliably.
- At 16×16 the PBM decodes held up: two exact, and the other two had 244 and 243 of 256 pixels right, one of them a noise image.
- BMP did better at low effort than at high (4 of 4 against 2 of 4). The two high-effort misses were small: 56 and 62 of 64 pixels. With four images per cell this may be noise.

### 5. PNG at high effort: Luna needs a very large reasoning allowance, and the compression inside the file decides the outcome

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

### 6. Decoding the pixels is not the same as recognising the picture

- GPT-6 Luna decoded the BMP of the X exactly and then called it "a white diamond on a black background".
- Luna decoded the PNG of the 7 exactly and described it as "a short horizontal bar with a zigzagging stem".
- GPT-6 Sol decoded the PNG of the 7 with the colours swapped (see finding 1).

## Cost and time

| Model | Calls | Spend |
|---|---|---|
| GPT-6 Luna | 92 | $0.316 |
| Claude Sonnet 5.5 | 14 | $0.286 |
| GPT-6 Sol | 11 | $0.202 |
| Gemini 3.8 Flash | 11 | $0.160 |
| **Total** | **128** | **$0.965** |

- Cost is almost entirely reasoning tokens. A no-reasoning call costs a fraction of a cent on any model.
- 23 Luna calls were cut off at a token cap with no answer. They are billed all the same and cost $0.19.
- One call timed out (Luna, `shape_x` 8×8 PNG, third run). The runner stopped and logged it, and the call was resent successfully.

## Caveats

- Sonnet, Sol and Gemini have one run per cell and two images per format. The pattern is clear, but the counts are small.
- All images are 8×8 or 16×16 and black-and-white, about 20–130 characters of base64. A real photo is hundreds of thousands of characters; nothing here says these results carry over.
- Pixel accuracy flatters sparse shapes: an all-white reply scores about 80% on a digit. The exact-decode counts and the noise images are the numbers to trust.
- The token cap also limits how long a model can think, so a failure at the cap (Luna on PNG, Gemini) is "did not finish", not "cannot".
- Models were not all run at the same effort level, because each has a different range. Rows compare each model at a setting where it reasons.
