# Anti-Engagement-Farm

A Manifest V3 Chrome extension that hides engagement-bait tweets ("like and retweet", "tag a friend", reply-bait questions) on twitter.com and x.com. Classification runs entirely on your machine: a fine-tuned BERT classifier (int8 ONNX, about 2 ms CPU per tweet), served by a local FastAPI server. No API keys, no cloud calls, no tracking. Fully open source, Apache-2.0.

## How it works

- `extension/content.js` observes tweets as they appear in the timeline.
- `extension/service_worker.js` sends each tweet text to the local server.
- `server.py` runs the ONNX model (downloaded from Hugging Face) and returns hide/label/prob.
- The popup has the ON/OFF toggle and shows the log of hidden tweets.

## Quick start

1. Clone the repo and cd into it:
   ```sh
   git clone <repo-url>
   cd anti-engagement-farming-chrome-extension
   ```
2. Start the backend:
   ```sh
   ./start.sh
   ```
   First run creates `.venv`, installs dependencies, and downloads the ~42 MB int8 ONNX model from Hugging Face. Then it serves on http://127.0.0.1:8000.
3. Open `chrome://extensions`, enable Developer mode, click "Load unpacked", and select the `extension/` folder.
4. Open the popup, click Turn ON, and browse X.

Note: keep `start.sh` running while browsing. The extension needs the local server.

## Benchmarks

Model and inference numbers, measured 2026-09-13 (details in `model/README.md`).

| Metric | Value |
| --- | --- |
| Base model | google/bert_uncased_L-8_H-512_A-8 (BERT-medium, 32M params), fine-tuned 6 epochs |
| Training data | 12,506 tweets collected, 7,766 usable at 0.85 teacher confidence (1,706 farming) after dedupe |
| Validation (777 rows, 189 farming) | precision 0.98, recall 0.90, F1 0.94 at threshold 0.5 |
| Held-out test (273 fresh timeline tweets, 15 farming, zero overlap) | precision 1.00, recall 0.47 at threshold 0.5 (recall 0.67 at 0.3) |
| Serving artifact | int8 ONNX, 42 MB |
| CPU inference | mean 1.9 ms, p95 2.7 ms per tweet |

Through the HTTP API (FastAPI + uvicorn, localhost, 200 sequential requests): p50 2.3 ms, p95 3.1 ms end to end per request.

Notes:

- We ship threshold 0.5 even though recall is higher at 0.3, because a false positive hides a genuine tweet.
- The held-out test set is fresh timeline tweets with zero overlap with training data.

## Configuration

- `server.py` environment variables:
  - `MODEL_DIR`: serve a local `model/model_out` copy instead of downloading from Hugging Face.
- `extension/service_worker.js`:
  - `BACKEND_URL`: classifier endpoint (default `http://127.0.0.1:8000/api/classify/`).

## API

`POST /api/classify/` with body `{"text": "..."}` returns:

```json
{"hide": true, "label": "engagement_farming", "prob": 0.97, "ms": 1.8}
```

`label` is `engagement_farming` or `genuine`, `prob` is the farming probability, `ms` is model inference time. Empty or invalid input returns 422. Interactive docs at http://127.0.0.1:8000/docs (FastAPI auto-generated).

## Development

- Server tests: `.venv/bin/python test_api.py`
- Extension smoke test: `node test/smoke.mjs`
- Syntax check: `node --check extension/service_worker.js`
- Model training pipeline (collect, label, train, evaluate, publish): see `model/README.md`

## License

Apache-2.0, covering code and model weights. Model on Hugging Face: https://huggingface.co/selftaughtdev/engagement-farm-classifier

Labels were distilled from an LLM teacher. Training scripts are included; tweet datasets are not redistributed.
