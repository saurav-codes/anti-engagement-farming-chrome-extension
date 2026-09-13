"""Batch-label tweets as engagement farming with a strong LLM teacher.

Usage:
    LABEL_API_KEY=... python label.py tweets.json --model kimi-k3

Any OpenAI-compatible endpoint works; --base-url overrides it
(default: OpenAI's API). Batches 20 tweets per request with
--workers batches in parallel. Writes labeled.json after every batch
(resumable: rerun skips labeled ids and retries null labels). Row shape:
{id, author, text, label, confidence}. train.py applies the confidence
cutoff (--min-confidence, default 0.85) at training time.
"""
import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI

INSTRUCTIONS = """You label tweets for an anti-engagement-farming product.

Engagement-farming tweets exist to drive likes, replies, retweets, shares, tags
or clicks rather than to convey genuine information, storytelling, opinion or
value. This includes:
1. Explicit calls to action: "Like if you agree!", "Retweet to bless someone!"
2. Implicit prompts with no substance: open-ended questions solely for replies
3. Giveaways or incentives: "RT and I'll follow back!", "Reply to win a prize!"
4. Emotional hooks with no new content: "This made me cry... thoughts?"
5. Low-effort filler or greetings: "Good morning everyone!"
6. Clickbait teasers: "You won't believe what happened next..."
7. Tag-a-friend / chain posts / polls purely for engagement
8. Any other tactic where the primary goal is metric boosting

You receive a JSON array of {"i": index, "text": tweet}. For each element, judge
whether the tweet's PRIMARY PURPOSE is engagement farming and how confident you
are. Respond with ONLY a JSON object:
{"results": [{"i": 0, "label": true, "confidence": 0.9}, ...]}
label is true for engagement farming, false for genuine, confidence in [0, 1].
Every input index must appear exactly once.

Examples:
"Like this if you love pizza" -> label true, confidence 0.99
"Which do you prefer, summer or winter? Vote in the replies!" -> label true, confidence 0.9
"I just rescued a kitten from the shelter and she's settling in." -> label false, confidence 0.95
"Our Q2 earnings report is now available: link." -> label false, confidence 0.9"""


def parse_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def coerce_label(raw):
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return {"true": True, "false": False}.get(raw.strip().lower())
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tweets", nargs="?", default="tweets.json")
    ap.add_argument("--out", default="labeled.json")
    ap.add_argument("--base-url", default=os.environ.get("LABEL_BASE_URL", "https://api.openai.com/v1"))
    ap.add_argument("--model", default=os.environ.get("LABEL_MODEL", "kimi-k3"))
    ap.add_argument("--batch-size", type=int, default=20)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    key = os.environ.get("LABEL_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit("set LABEL_API_KEY (or OPENAI_API_KEY)")
    client = OpenAI(base_url=args.base_url, api_key=key)
    with open(args.tweets) as f:
        tweets = json.load(f)
    done = {}
    if os.path.exists(args.out):
        with open(args.out) as f:
            done = {r["id"]: r for r in json.load(f)}
    todo = [
        t
        for t in tweets
        if t.get("id") and t.get("text") and (t["id"] not in done or done[t["id"]].get("label") is None)
    ]
    print(f"{len(done)} already labeled, {len(todo)} to go", file=sys.stderr)

    batches = [todo[i : i + args.batch_size] for i in range(0, len(todo), args.batch_size)]
    lock = threading.Lock()

    def label_batch(batch):
        for attempt in (1, 2):
            try:
                resp = client.chat.completions.create(
                    model=args.model,
                    messages=[
                        {"role": "system", "content": INSTRUCTIONS},
                        {
                            "role": "user",
                            "content": json.dumps(
                                [{"i": i, "text": t["text"]} for i, t in enumerate(batch)]
                            ),
                        },
                    ],
                )
                data = parse_json(resp.choices[0].message.content or "")
                return (
                    data.get("results", [])
                    if isinstance(data, dict)
                    else data
                    if isinstance(data, list)
                    else []
                )
            except Exception as e:
                if attempt == 2:
                    print(f"batch failed, skipping (rerun to retry): {e}", file=sys.stderr)
                    return []
                time.sleep(3)
        return []

    def handle(pair):
        index, batch = pair
        results = label_batch(batch)
        with lock:
            for r in results:
                i = r.get("i")
                if not isinstance(i, int) or not 0 <= i < len(batch):
                    continue
                t = batch[i]
                conf = min(max(float(r.get("confidence", 0)), 0.0), 1.0)
                done[t["id"]] = {
                    "id": t["id"],
                    "author": t["author"],
                    "text": t["text"],
                    "src": t.get("src"),
                    "label": coerce_label(r.get("label")),
                    "confidence": conf,
                }
            with open(args.out, "w") as f:
                json.dump(list(done.values()), f, indent=1)
            kept = sum(1 for r in done.values() if r["label"] is not None)
            print(
                f"[{min((index + 1) * args.batch_size, len(todo))}/{len(todo)}] {kept} usable",
                file=sys.stderr,
            )

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(handle, enumerate(batches)))

    farming = sum(1 for r in done.values() if r["label"] is True)
    genuine = sum(1 for r in done.values() if r["label"] is False)
    print(
        f"done: {len(done)} labeled, {farming} farming, {genuine} genuine, "
        f"{len(done) - farming - genuine} unlabeled",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
