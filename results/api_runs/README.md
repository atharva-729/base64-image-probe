# API runs: results

**Status:** complete. 218 replies from four models, 5–12 October 2026. Total spend: **$2.41**.

## The question, and the answer

**Question:** if a model is given only the text of an image file (base64), with no tools and no image input, can it work out what the picture is?

**Answer:** yes, for tiny images, when the model reasons. On seven 8×8 images in five formats, GPT-6 Sol decoded all 35 and Claude Sonnet 5.5 decoded 33. Both decoded all three compressed PNGs of random noise, which cannot be guessed.

![Share of images decoded exactly, by model and format](accuracy.svg)

![Average cost of one call, by model and format](cost.svg)

How to read the charts:

- **Rows** are models, each at the reasoning effort where it works, plus GPT-6 Luna with reasoning off as a baseline.
- **Columns** are ways of storing the same picture, easiest to hardest. The text grid is the picture typed out as 0s and 1s (a sanity check). PBM, PGM and BMP list the pixels uncompressed. PNG compresses them, so the model has to decompress in its reasoning.
- **Seven images** per cell: a 1, a 7, a cross, a circle and three blocks of random noise, one run each. The reasoning-off baseline was run on four of them.
- **"Decoded"** means every one of the 64 pixels is right. A grid that is exact with black and white swapped counts, and is labelled.

## Main findings

1. **GPT-6 Sol decoded everything: 35 of 35.** That includes all three noise PNGs. No tools were available, so this is reasoning alone.
2. **Claude Sonnet 5.5 decoded 33 of 35.** It got every noise PNG and missed two shape PNGs by two and three pixels.
3. **Without reasoning, nothing decodes.** GPT-6 Luna with reasoning off got the text grid and nothing else.
4. **PNG is the expensive format.** For Sol and Sonnet a PNG takes about 45 seconds and 4–7 cents, against seconds and under a cent for PBM.
5. **GPT-6 Luna is solid on simple formats and fades after.** 7 of 7 on PBM, 5 on PGM, 3 on BMP, 2 on PNG, at about a quarter of Sol's cost.
6. **Gemini 3.8 Flash at low effort is unreliable past PBM.** It got 0 of 7 PNGs, and 10 of its 16 misses came with high confidence.

**What this is not.** It is not advice on how to send images to a model. Attaching an image normally uses the model's vision input, which is far cheaper and more reliable. The experiment measures how far text-only reasoning goes on raw file bytes.

## The numbers

| Model | Effort | Format | Decoded | Avg. cost per call | Avg. reasoning tokens | Avg. time |
|---|---|---|---|---|---|---|
| Claude Sonnet 5.5 | high effort | Text grid | 7 of 7 | $0.002 | 0 | 3 s |
| Claude Sonnet 5.5 | high effort | PBM | 7 of 7 | $0.008 | 577 | 7 s |
| Claude Sonnet 5.5 | high effort | PGM | 7 of 7 | $0.032 | 2,984 | 21 s |
| Claude Sonnet 5.5 | high effort | BMP | 7 of 7 | $0.018 | 1,460 | 13 s |
| Claude Sonnet 5.5 | high effort | PNG | 5 of 7 | $0.069 | 6,640 | 50 s |
| GPT-6 Sol | medium effort | Text grid | 7 of 7 | $0.002 | 110 | 3 s |
| GPT-6 Sol | medium effort | PBM | 7 of 7 | $0.005 | 392 | 7 s |
| GPT-6 Sol | medium effort | PGM | 7 of 7 | $0.017 | 1,613 | 16 s |
| GPT-6 Sol | medium effort | BMP | 7 of 7 | $0.010 | 886 | 10 s |
| GPT-6 Sol | medium effort | PNG | 7 of 7 | $0.044 | 4,287 | 45 s |
| GPT-6 Luna | high effort | Text grid | 7 of 7 | under $0.001 | 749 | 10 s |
| GPT-6 Luna | high effort | PBM | 7 of 7 | $0.001 | 1,663 | 18 s |
| GPT-6 Luna | high effort | PGM | 5 of 7 | $0.004 | 7,934 | 67 s |
| GPT-6 Luna | high effort | BMP | 3 of 7 | $0.005 | 10,767 | 94 s |
| GPT-6 Luna | high effort | PNG | 2 of 7 | $0.010 | 19,792 | 165 s |
| Gemini 3.8 Flash | low effort | Text grid | 7 of 7 | $0.001 | 217 | 3 s |
| Gemini 3.8 Flash | low effort | PBM | 6 of 7 | $0.009 | 2,077 | 13 s |
| Gemini 3.8 Flash | low effort | PGM | 2 of 7 | $0.026 | 6,807 | 42 s |
| Gemini 3.8 Flash | low effort | BMP | 4 of 7 | $0.024 | 6,094 | 38 s |
| Gemini 3.8 Flash | low effort | PNG | 0 of 7 | $0.014 | 3,486 | 23 s |
| GPT-6 Luna | reasoning off | Text grid | 4 of 4 | under $0.001 | 0 | 2 s |
| GPT-6 Luna | reasoning off | PBM | 0 of 4 | under $0.001 | 0 | 2 s |
| GPT-6 Luna | reasoning off | PGM | 0 of 4 | under $0.001 | 0 | 2 s |
| GPT-6 Luna | reasoning off | BMP | 0 of 4 | under $0.001 | 0 | 2 s |
| GPT-6 Luna | reasoning off | PNG | 0 of 4 | under $0.001 | 0 | 2 s |

| Model | Effort | Decoded | Avg. cost per call | Total for the 35 calls |
|---|---|---|---|---|
| GPT-6 Sol | medium | 35 of 35 | $0.015 | $0.54 |
| Claude Sonnet 5.5 | high | 33 of 35 | $0.026 | $0.91 |
| GPT-6 Luna | high | 24 of 35 | $0.004 | $0.15 |
| Gemini 3.8 Flash | low | 19 of 35 | $0.015 | $0.52 |

## Setup

Each model gets one text prompt through the OpenRouter API and returns text. No tools are passed, so it cannot run a decoder. This closes the gap in the earlier chat-app runs, where the chatbot could have used code.

- **Prompt:** the model writes out the pixel grid (1 = black), then names the image and its confidence.
- **Images:** four shapes and three random-noise images, all 8×8. Noise has no shape to guess; chance is 50% per pixel.
- **Reasoning effort** is set per call. Sonnet 5.5 and Gemini 3.8 Flash cannot switch reasoning off through the API.
- **Token caps** for the final round, set by price: 32,000 for Luna, 10,000 for Gemini at low effort, 12,000 for Sol and Sonnet. Three of Luna's PNG cells are earlier calls made at a 24,000 cap.
- **Scoring:** the grid in the reply is compared with the true pixels.

Every request and reply is in [responses.jsonl](../../responses.jsonl); per-reply scores are in [results.csv](../../results.csv). The charts and table are rebuilt by `make_table.py`. The technical background and the full history of the project are in the [main README](../../README.md).

## Findings in detail

### 1. GPT-6 Sol

- 35 of 35, at an average of 1.5 cents a call. Its most expensive call was 8,881 tokens for a noise PNG.
- **Colour swaps on PNG.** Four of its seven PNG grids were exact with black and white swapped. PNG stores 0 as black and the prompt asks for 1 as black, so this is a prompt trap as much as a model error. It did not happen in the other formats.
- With reasoning off (one call, the PNG of the 7) it declined to guess.

### 2. Claude Sonnet 5.5

- 33 of 35 at high effort, at 2.6 cents a call. The two misses were PNGs: the 1 (61 of 64 pixels) and the cross (62 of 64). All three noise PNGs were exact.
- **It needs high effort.** At low and medium it did no reasoning on the PNG of the 7 (zero reasoning tokens in four calls). Twice it refused to give a grid, saying it would be fabrication; twice it gave a grid labelled as a guess with low confidence.
- It never stated high confidence on a wrong answer.

### 3. GPT-6 Luna

The cheapest model, so it was also swept across reasoning settings on four images (the 7, the cross, two noise images). Exact decodes out of 4:

| Format | Reasoning off | Low | High |
|---|---|---|---|
| Text grid | 4 | 4 | 4 |
| PBM | 0 | 2 | 4 |
| PGM | 0 | 0 | 4 |
| BMP | 0 | 4 | 2 |
| PNG | 0 | 0 | 5 of 12 (three runs) |

- **Reasoning is the switch.** With it off, Luna got 0 of 16 encoded images at 38–67% pixel accuracy, and stated high confidence on 6 of them.
- **On the seven-image set at high effort** it got 24 of 35. Its BMP misses were mostly a few pixels off.
- **PNG is at the edge of its reach.** With a 12,000-token cap, 15 of 16 PNG calls used the whole cap and returned nothing. Resent at 24,000, 6 of those 15 came back exact, 1 declined and 8 were cut off again. The same call can succeed on one run and fail on the next.
- **When it finishes a PNG it is usually right:** 8 of the 10 PNG grids it produced were pixel-perfect. The two wrong ones were the 1 (61 of 64) and the circle (48 of 64).
- **The compression inside the PNG matters.** Both 16×16 PNGs that store their pixels uncompressed were decoded exactly; the fixed-Huffman 8×8 ones succeeded on some runs; the one dynamic-Huffman file was not decoded. The block types were read from the files; that they explain the pattern is an inference.

### 4. Gemini 3.8 Flash

- **At low effort** it got 19 of 35: all the text grids, 6 of 7 PBM, 4 of 7 BMP, 2 of 7 PGM and no PNGs. How much it reasoned varied from call to call, from nothing to nearly its whole 10,000-token cap.
- **Confident wrong answers.** 10 of its 16 misses came with high confidence, including a "smiley face" for the PNG of the 7.
- **At medium effort** (one call, the PNG of the 7) it used its whole 12,000-token cap and gave an invented decode of an "X" with high confidence. Medium was not run further because of cost.
- In the earlier chat-app run, Gemini with extended thinking took nearly six minutes and got that image right, so more reasoning than we gave it may be what it needs.

### 5. Decoding the pixels is not the same as recognising the picture

- GPT-6 Luna decoded the BMP of the cross exactly and called it "a white diamond on a black background".
- Luna decoded the PNG of the 7 exactly and described it as "a short horizontal bar with a zigzagging stem".
- GPT-6 Sol's colour-swapped PNGs are exact decodes read with the wrong convention.

## Cost and time

| Model | Calls | Spend |
|---|---|---|
| Claude Sonnet 5.5 | 39 | $0.92 |
| Gemini 3.8 Flash | 36 | $0.57 |
| GPT-6 Sol | 36 | $0.54 |
| GPT-6 Luna | 107 | $0.38 |
| **Total** | **218** | **$2.41** |

- Cost is almost entirely reasoning tokens. A no-reasoning call costs a fraction of a cent on any model.
- 23 of Luna's early calls were cut off at a token cap with no answer. They are billed all the same and cost $0.19. None of the 90 calls in the final round was cut off.
- One call timed out (Luna, cross PNG, third run). The runner stopped and logged it, and the call was resent successfully.

## Caveats

- Seven images with one run per cell. Luna's repeat runs show a single call can go either way, so small differences between models should not be read into.
- All images are 8×8 or 16×16 and black-and-white, about 20–130 characters of base64. A real photo is hundreds of thousands of characters; nothing here says these results carry over.
- Pixel accuracy flatters sparse shapes: an all-white reply scores about 80% on a digit. The exact-decode counts and the noise images are the numbers to trust.
- The token cap also limits how long a model can think, so a failure at the cap is "did not finish", not "cannot".
- Models were not all run at the same effort level, because each has a different range. Rows compare each model at a setting where it reasons.
