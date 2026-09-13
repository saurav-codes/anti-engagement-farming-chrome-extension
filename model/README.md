# Engagement-farm classifier model

Small open-source model that labels X (Twitter) posts as engagement farming or genuine. Target: under 50 MB, CPU inference well inside 10-300 ms. Pipeline: collect raw tweets from the timeline -> label once with a strong LLM teacher -> fine-tune BERT-mini -> export int8 ONNX. No per-request LLM cost afterwards.

Standalone: nothing here depends on the extension or backend code. Move this folder anywhere.

## 1. Collect

Paste `collect_tweets.js` into the console on x.com (logged in), then:

```js
__farmCollector.start(2000)   // auto-scrolls and collects up to 2000 tweets
__farmCollector.stop()        // stop scrolling
__farmCollector.download()    // saves tweets.json
```

Notes:

- Resumable: data survives refreshes (localStorage). Run `start()` again to continue.
- Any Chromium browser works, including ego-browser, where an agent can drive the whole collection for you.
- Vary the data by switching between Following / For You, accounts, and lists. Bait-heavy lists balance the positives; timelines are usually under 10% farming.
- Each tweet is saved as `{id, author, text}`. Promoted posts stay in; the teacher labels most of them true, which is fine for this task.

## 2. Label

```bash
pip install openai
LABEL_API_KEY=... python label.py tweets.json --model kimi-k3
```

Any OpenAI-compatible endpoint works (`--base-url` overrides; default is OpenAI's API). Batches 20 tweets per request with several batches in parallel (`--workers`, default 6), and writes `labeled.json` after every batch, so it is resumable (rerun skips done ids and retries null labels). Every row keeps the teacher's raw verdict plus confidence; the confidence cutoff is applied at training time (`train.py --min-confidence`, default 0.85). Roughly 10k tweets is one evening of scrolling and a few dollars of labeling.

## 3. Train

```bash
pip install torch transformers optimum[onnxruntime] onnxruntime
python train.py labeled.json
```

Fine-tunes `google/bert_uncased_L-4_H-256_A-4` (BERT-mini, 11M params) by default; the shipped model used `--base google/bert_uncased_L-8_H-512_A-8` (BERT-medium, 32M params, consistently more precise on held-out data). Prints validation accuracy and F1, and writes:

- `model_out/` PyTorch checkpoint + tokenizer (this is what you upload to Hugging Face)
- `model_out/onnx/` fp32 ONNX (~165 MB for medium)
- `model_out/onnx-int8/` int8 ONNX (~42 MB for medium), the serving artifact

`python eval.py` reruns the threshold sweep on the validation split.

## Results (2026-09-13)

12,506 tweets collected (timeline scrolling plus ~36 bait-phrase search queries covering explicit CTAs, subtle question bait, giveaways, reply chains, and greeting filler), labeled by kimi-k3, 7,766 usable at 0.85 confidence (1,706 farming) after text dedupe.

Serving model: `google/bert_uncased_L-8_H-512_A-8` (BERT-medium, 32M params), 6 epochs. Validation (777 rows, 189 farming): precision 0.98, recall 0.90, F1 0.94 at threshold 0.5.

Held-out benchmark (`test_labeled.json`, 273 fresh timeline tweets with zero id/text overlap with training, 15 farming): precision 1.00 with zero false positives, recall 0.67 at threshold 0.3, 0.47 at the default 0.5. The test positives are the subtle, timeline-native kind (rhetorical "how many of you" questions, greeting fillers), so this recall is the realistic number. Since a false positive hides a genuine tweet, ship at threshold 0.5 and treat lower thresholds as a tunable knob.

Artifact: `model_out/onnx-int8/` int8 ONNX, 42 MB, single-tweet CPU latency mean 1.9 ms, p95 2.7 ms. `eval.py --labeled test_labeled.json --full` reruns the held-out sweep.

## 4. Publish

```bash
pip install huggingface_hub
hf auth login
hf upload <your-user>/engagement-farm-classifier model_out . --repo-type model
```

Model card must state: labels are distilled from a proprietary LLM teacher, training script included, and no raw tweet corpus is redistributed (tweet text is platform data; ship scripts, not datasets).
