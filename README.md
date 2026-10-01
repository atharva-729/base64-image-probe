# Can LLMs See Images Through Base64?

## The question

If you give a frontier LLM the **base64 text of an image file**, with no tools and no image input, can it work out what the image shows?

Models are surprisingly fluent at reading and writing base64. If that fluency extends far enough, a model might decode an image file into pixels "in its head" and recognize the picture. That's an image read entirely through the text pathway, never touching the vision encoder.

## Why it's interesting

- **Capability probe.** It tests how far a model's text-only reasoning can go on raw binary data, which says something about what these models have actually learned.
- **Text pathway vs. vision pathway.** One hypothesis from the discussion was that models internally "render" base64 into an image. This experiment, together with the token check below, can test that. Raw models don't route text into the vision encoder. If recognition happens at all, it comes from text reasoning.
- **Representation cost.** It ties into the broader "same content, different encoding" question, the image version of PDF vs. Markdown: what does each representation cost in tokens, and what does the model get right with it?

## Key idea: file format decides difficulty

Not all image formats are equally hard to decode by hand.

| Format | What the bytes contain | Decoding difficulty |
|---|---|---|
| Text grid (0s and 1s) | Pixels written as characters | Trivial (control) |
| PGM / PBM / BMP | Small header, then raw pixel values | Tedious but possible: base64 → bytes → pixel values → picture |
| PNG | DEFLATE-compressed pixel data | Near impossible: requires decompressing in its head |
| JPEG | DCT-compressed, lossy | Effectively impossible |

**Hypothesis:** models succeed on the grid, sometimes succeed on raw-pixel formats for tiny images, and fail on PNG/JPEG.

## Method

### 1. Build test images
Start with tiny, unambiguous black-and-white images:
- Digits: `1`, `7`, `0`
- Shapes: `X`, square, diagonal line, circle
- Sizes: 8×8, then 16×16, then 32×32

Use a fixed, known set so results are comparable across models.

### 2. Encode each image several ways
For each image, produce:
1. **Text grid**: rows of `0`/`1` characters (control: no decoding needed)
2. **PBM/PGM, base64-encoded**: raw-pixel format with the simplest possible header
3. **BMP, base64-encoded**: raw pixels, slightly messier header and padding
4. **PNG, base64-encoded**: compressed

### 3. Prompt the models (no tools)
Use plain chat with code execution, search and file tools **off** where possible. Otherwise, explicitly say "do not run any code or use tools."

Prompt template:
```
The following is a base64-encoded <FORMAT> image file. Without using any tools,
tell me what the image shows. Then give your confidence (low/medium/high).

<BASE64 STRING>
```

Variants to try:
- **Blind:** don't name the format; see whether it identifies the format from the header bytes
- **Guided:** name the format and the dimensions
- **Show work:** ask it to reconstruct the pixel grid first, then identify the image. This separates "decoded correctly" from "guessed"

### 4. Models to test
Whatever's available: Claude, ChatGPT, Gemini (AI Studio is free). Use the same images and prompts for every model.

### 5. Climb the ladder
Only move to the next rung once a model passes the current one:
grid → raw-pixel 8×8 → raw-pixel 16×16 → raw-pixel 32×32 → grayscale → PNG

## What to record

For each (model × image × format × prompt variant):
- **Correct?** Did it name the right digit or shape?
- **Grid reconstruction accuracy** (show-work variant): fraction of pixels correct
- **Stated confidence:** does it know when it's guessing?
- **Hallucination:** did it confidently describe something that isn't there?
- **Token count** of the input (see below)

A simple results table is enough:

| Model | Image | Size | Format | Variant | Correct | Pixel acc. | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|

## Token cost side-measurement (no API needed)

- **Base64 text:** count tokens locally with `tiktoken`. Claude's tokenizer differs, but the ballpark is the same.
  ```python
  import tiktoken
  enc = tiktoken.get_encoding("o200k_base")
  print(len(enc.encode(b64_string)))
  ```
- **Native image:** use published formulas. Claude ≈ width × height / 750 tokens; OpenAI = 85 + 170 per 512px tile.
- **Empirical check:** Google AI Studio shows live token counts. Paste the base64 string, then upload the same image, and compare.

Expectation: base64 costs far more tokens than the native image for anything beyond tiny images. That also answers whether "image → text string" is a useful trick the way "PDF → Markdown" is (probably not).

## Gotchas

- **Tool leakage:** if code execution is on, the model will just write a decoder. That's a different experiment. Make sure tools are off, or check the transcript for tool calls.
- **Guessing from priors:** an 8×8 image of "1" is easy to guess. Use the show-work variant and a few less obvious shapes so lucky guesses don't count as decoding.
- **Header memorization:** a model may recognize `iVBORw0KGgo` as a PNG signature without decoding anything else. Identifying the format ≠ seeing the image.
- **Context limits:** base64 grows fast. A 32×32 PNG is fine, but a real photo may exceed what chat UIs accept.

## Possible outcomes

- **Fails everywhere except the grid:** models can't do binary decoding in context. The "they read base64 like crazy" fluency is mostly about text payloads.
- **Succeeds on raw-pixel formats at small sizes:** real in-context decoding ability. Find the size where it breaks.
- **Succeeds on PNG:** very surprising. Double-check for tool use and memorization before believing it.

## Related experiments from the same discussion

- **Multi-image order:** when given several images, do models and harnesses keep track of which is "image 1", "image 2", and so on, especially when filenames conflict with position?
- **Harness PDF handling:** do Claude Code / Codex read PDFs directly or convert them with a tool first? Watch the tool calls.
