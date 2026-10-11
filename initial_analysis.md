I decoded the PNG myself to get the ground truth. It's a 1-bit grayscale 8×8 image, and the checksums are valid. Here's how each model did.

**Ground truth** (1 = black):
```
01111110
00000110
00000100
00000100
00001000
00001000
00011000
00010000
```

| Model | Pixel grid | Answer | Confidence | Verdict |
|---|---|---|---|---|
| Claude Opus 5.5 (medium) | Exact, 64/64 | 7 | High | Fully decoded |
| Gemini 3.8 Flash, extended thinking | Exact, 64/64 | 7 | High | Fully decoded, and it explained the inversion |
| ChatGPT | Exact but inverted | "mostly black shape" | Medium-low | Decoded perfectly, then failed on the colours |
| Gemini 3.8 Flash (no thinking) | A ring, unrelated | O | High | Hallucinated |
| Gemini 3.6 Flash | Invented bytes | C | High | Hallucinated a fake decode |

**What's actually going on**

1. **My README prediction was wrong.** I called PNG decoding "near impossible." For an 8×8 1-bit image, the compressed data is only about 24 bytes, using the simple built-in compression tables, so it's tedious but tractable. Two models decoded every pixel exactly, so they weren't guessing "7" from the bar-and-diagonal shape. They genuinely decompressed the data and undid the filters. Rows 3–8 use PNG's "Up" filter, where each row is stored as a difference from the row above. That's a trap, and both models got through it.

2. **ChatGPT's grid isn't wrong, it's the raw file values.** In a grayscale PNG, 0 means black, and your prompt said 1 means black. ChatGPT output the stored values without flipping them, so it saw a white 7 on a black background and couldn't recognize it. It also claimed the compressed data's checksum was inconsistent. That's false: it verifies fine. So the decoding was perfect, but the interpretation and the self-checking failed. Gemini with thinking noticed exactly this trap and wrote it out. This is a confound in your prompt. Next time, score decoding and interpretation separately, or don't fix a colour convention in the prompt.

3. **Thinking is the dividing line.** Every model that reasoned for a while got the pixels right. The two instant answers fabricated something. Gemini 3.6 even wrote a convincing step-by-step "decompression" with made-up bytes and a "filter 00 on every row" claim that's wrong. The scariest part: both hallucinations came with high confidence. That calibration gap is arguably your most interesting finding so far.

4. **Time is a rough measure of effort.** Claude took 43 seconds and Gemini with thinking took 5 minutes 50 seconds for the same correct result. The instant answers were wrong. That's worth a column in the results table.

**Caveats:** this is one image and one run per model. A "7" is also a common shape, so a model could guess it. The exact pixel matches argue against guessing here, but it's still a risk in general.

**What I'd test next**

- **Random-noise images.** An 8×8 grid of random pixels gives a model no shape to guess from, so pixel accuracy is the only thing that counts. This is the cleanest test of real decoding.
- **Go bigger:** 16×16, then 32×32. Larger PNGs switch to custom compression tables (dynamic Huffman) and mix filter types, which is where I'd expect even the thinking models to break.
- **Non-thinking models on the PBM/BMP versions.** This tells you whether their failure comes from the PNG compression or just from answering without reasoning.
- **Re-run each condition 2–3 times.** Some of these answers could be lucky or unlucky runs.

I can update the README with these results, the colour-convention fix, and the revised hypothesis, and generate the noise images and the 16×16 set.