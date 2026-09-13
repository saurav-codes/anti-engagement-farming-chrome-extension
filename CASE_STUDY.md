# Anti-Engagement-Farm: from GPT-4o prototype to a 42MB local classifier

## At a glance

| Item | Value |
| --- | --- |
| Tech stack | MV3 extension + FastAPI + ONNX int8 BERT |
| Model size | 42MB |
| Inference | 1.9ms raw / 17ms under scroll load |
| RAM | 209MB |
| Detection | 4.5% of timeline was bait (precision 1.00 held-out) |
| License | Apache-2.0 |
| API keys | 0 |

## 1. The problem

Engagement-bait tweets clog the timeline. "Like and retweet." "Tag a friend." Reply-bait questions dressed up as conversation. The answer-bait posts that exist only to farm numbers.

The first attempt at this, built years ago before July 2024, was a Django backend that sent every tweet to OpenAI GPT-4o. A regex prefilter tried to cut costs, and every single tweet got logged to SQLite for auditing. It worked, sort of. It was slow, it cost money per tweet, and it needed an API key for something a small local model can do better.

## 2. Training the model

This week I rebuilt the classifier from scratch.

The scraper, `collect_tweets.js`, pulled 12,506 posts from the timeline and keyword searches. `label.py` used kimi-k3 as the LLM teacher over an OpenAI-compatible API, with a 5% confidence sampling pass. After filtering at confidence >= 0.85, that left 7,766 usable examples with 1,706 farming labels.

The model is google/bert_uncased_L-8_H-512_A-8 (BERT-medium, 32M parameters), fine-tuned for 6 epochs on Apple Silicon MPS. Exported to ONNX with int8 quantization, the serving artifact is 42MB.

On the validation split (777 rows, 189 farming) it hit precision 0.98, recall 0.90, F1 0.94 at threshold 0.5. On a held-out test of 273 fresh timeline tweets (15 farming, zero overlap with training), precision was 1.00 and recall 0.47 at threshold 0.5. It misses some bait, but what it flags is bait. CPU inference runs at a 1.9ms mean with a 2.7ms p95.

That asymmetric error profile is fine for a hiding filter. Better to let some bait through than to hide real posts.

## 3. Two refactors

The first refactor deleted the OpenAI path entirely and served the ONNX model from the existing Django app. Logging moved to plain Python logging, and I deleted DRF and the ApiCall audit table. The audit table existed to debug a paid API. With a local model, it was dead weight.

The second refactor deleted Django entirely. What remained was a single-file FastAPI server, `server.py`, running a raw `onnxruntime.InferenceSession`. No optimum wrapper, no torch at inference time. The model auto-downloads from Hugging Face at startup, the threshold is 0.5, and bad input returns a 422.

The extension got cleaned up in the same sweep. I deleted the regex prefilter, the 100-char skip gate, and the response cache. All three were workarounds from the GPT-4o era, where every call cost money and latency. With local inference at 2ms, they were obsolete complexity. Logging also got unified under one `[AEF]` prefix.

## 4. Open-source packaging

Packaging was about making it runnable by a stranger.

`start.sh` sets up a uv venv with a python3 fallback, installs dependencies, and launches uvicorn on 127.0.0.1:8000. `requirements.txt` has 6 dependencies. `test_api.py` is a plain script that hits the API, no test framework required. The license is Apache-2.0, chosen to match the model license.

The extension moved into `extension/`. The `.gitignore` ships the scripts but keeps 357MB of weights and scraped data out of the repo. The README got a proper OSS header: centered logo, badges. For the walkthrough, a 458MB demo recording got compressed down to an 8.9MB `demo.gif`. There is also an animated benchmark diagram built with archify, `benchmark.gif` at 871KB.

## 5. UI pass

The logo came from one Stable Diffusion 3.5 generation: a blue shield with a crossed-out megaphone. The ON and OFF icon variants were derived deterministically from that single image at 16/32/48/128px, ON colored and OFF grayscale. One generation, then math, beat spending an hour regenerating.

The popup went from a bare toggle to a real design: a blocked count and an iOS-style switch, with an OFF view that shows a trash illustration. Motion concepts came from fluidfunctionalism: spring tokens at 80/160ms, a single gliding hover highlight, a thin scrollbar that widens on hover, and a CSS mask scroll fade at the edges.

Verification caught two real bugs. First, duplicate log entries: X regenerates DOM nodes as you scroll, so the same tweet got processed and logged more than once. Fixed by making the storage write idempotent, keyed by tweet id. Second, a feature that landed the same day: clicking a card in the popup opens the blocked tweet in a new tab.

## 6. Real-world benchmark

For the real test, I scrolled X live for about 8 minutes while the server logged every request.

The numbers: 3,198 classifications, p50 of 17ms, p95 of 40ms, max of 72ms. The idle benchmark sat at a p50 of 2.3ms, so the gap is Chrome rendering competing for CPU, not the model. Average load was 6.6 requests per second, with peak bursts at 36 requests per second. Total RAM for the whole stack was 209MB.

It caught 144 bait tweets, 4.5% of the timeline, one in 22 posts, at an average confidence of 0.942.

One honest flaw surfaced: 949 of those requests were redundant re-checks, because X re-renders its DOM constantly and the extension re-sends what it already saw. A seen-tweet cache is the next optimization. Funny enough, I deleted the old cache in the refactor. Now a new, simpler one has a legitimate reason to exist.

## 7. Launch

The model is published on Hugging Face as `selftaughtdev/engagement-farm-classifier` under Apache-2.0. The repo lives on GitHub at `saurav-codes/anti-engagement-farming-chrome-extension`. Announcements went out on X and LinkedIn with the animated archify diagram explaining the pipeline.

## Lessons

- Keep scripts in git and weights in a model registry. The repo stays lean and cloneable.
- One AI image generation plus deterministic variants beats many generations. Decide once, derive the rest.
- Browser screenshots catch what tests cannot. Both bugs found in the UI pass were visible-only problems.
- A 2ms inference model still needs a client cache when the platform re-renders everything. Fast inference does not save you from redundant requests.
