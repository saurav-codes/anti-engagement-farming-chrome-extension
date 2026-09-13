"""Evaluate the trained ONNX model on the validation split with a threshold sweep.

Usage: python eval.py [--thresholds 0.5,0.4,0.3,0.2] [--min-confidence 0.85]

Mirrors train.py's split (same seed, filter, dedup) so the rows match training.
The serving threshold is a deployment choice: lower it to hide more bait at the
cost of hiding more genuine tweets.
"""
import argparse
import glob
import json
import os
import random

import numpy as np
from optimum.onnxruntime import ORTModelForSequenceClassification
from transformers import AutoTokenizer

SEED = 13


def val_rows(rows, min_conf, full=False):
    data = [
        r
        for r in rows
        if r.get("label") is not None and r.get("text") and r.get("confidence", 1.0) >= min_conf
    ]
    seen, deduped = set(), []
    for r in data:
        if r["text"] not in seen:
            seen.add(r["text"])
            deduped.append(r)
    random.Random(SEED).shuffle(deduped)
    return deduped if full else deduped[int(len(deduped) * 0.9) :]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="model_out")
    ap.add_argument("--labeled", default="labeled.json")
    ap.add_argument("--thresholds", default="0.5,0.4,0.3,0.2")
    ap.add_argument("--min-confidence", type=float, default=0.85)
    ap.add_argument("--full", action="store_true", help="evaluate all rows, skip the 90/10 val split")
    args = ap.parse_args()
    thresholds = [float(t) for t in args.thresholds.split(",")]

    d = args.dir
    files = glob.glob(os.path.join(d, "onnx-int8", "*.onnx"))
    if not files:
        raise SystemExit(f"no artifacts in {d}/onnx-int8, run train.py first")

    val = val_rows(json.load(open(args.labeled)), args.min_confidence, args.full)
    onnx_file = max(files, key=os.path.getsize)
    model = ORTModelForSequenceClassification.from_pretrained(
        os.path.dirname(onnx_file), file_name=os.path.basename(onnx_file)
    )
    tok = AutoTokenizer.from_pretrained(d)
    labels = np.array([int(bool(r["label"])) for r in val])
    probs = np.array(
        [
            float(
                model(**tok(r["text"], return_tensors="pt", truncation=True, max_length=128)).logits.softmax(-1)[0, 1]
            )
            for r in val
        ]
    )
    print(f"{d} (min_conf {args.min_confidence}): val {len(val)} rows, {int(labels.sum())} farming")
    sweep(labels, probs, thresholds)
    clean = [(l, p) for r, l, p in zip(val, labels, probs) if r.get("src") == "timeline"]
    if clean:
        clabels = np.array([l for l, _ in clean])
        cprobs = np.array([p for _, p in clean])
        print(f"clean-timeline-only: {len(clean)} rows, {int(clabels.sum())} farming")
        sweep(clabels, cprobs, thresholds)


def sweep(labels, probs, thresholds):
    for t in thresholds:
        preds = (probs >= t).astype(int)
        tp = int(((preds == 1) & (labels == 1)).sum())
        fp = int(((preds == 1) & (labels == 0)).sum())
        fn = int(((preds == 0) & (labels == 1)).sum())
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        print(f"  t={t}: TP={tp} FP={fp} FN={fn} precision={prec:.2f} recall={rec:.2f} f1={f1:.2f}")


if __name__ == "__main__":
    main()
