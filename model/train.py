"""Fine-tune a small BERT on labeled tweets and export a quantized ONNX classifier.

Usage:
    python train.py labeled.json --base google/bert_uncased_L-4_H-256_A-4 --out model_out

Reads labeled.json from label.py, filters rows by --min-confidence
(default 0.85), trains a 90/10 split, prints validation accuracy/F1, and
writes:
- model_out/          PyTorch checkpoint + tokenizer (upload this to Hugging Face)
- model_out/onnx/     fp32 ONNX
- model_out/onnx-int8/  int8 ONNX, the serving artifact (~12 MB for BERT-mini)
"""
import argparse
import json
import os
import platform
import random

import numpy as np
import torch
from optimum.onnxruntime import ORTModelForSequenceClassification, ORTQuantizer
from optimum.onnxruntime.configuration import AutoQuantizationConfig
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

SEED = 13
MAX_TOKENS = 128  # tweets are short; 128 covers nearly all of them


class TweetDataset(torch.utils.data.Dataset):
    def __init__(self, rows, tokenizer):
        self.encodings = tokenizer([r["text"] for r in rows], truncation=True, max_length=MAX_TOKENS)
        self.labels = [int(bool(r["label"])) for r in rows]

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, i):
        item = {k: torch.tensor(v[i]) for k, v in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[i])
        return item


def metrics(eval_pred):
    preds = np.argmax(eval_pred.predictions, axis=1)
    labels = eval_pred.label_ids
    tp = int(((preds == 1) & (labels == 1)).sum())
    fp = int(((preds == 1) & (labels == 0)).sum())
    fn = int(((preds == 0) & (labels == 1)).sum())
    return {
        "accuracy": float((preds == labels).mean()),
        "f1": 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0,
    }


def onnx_path(directory):
    return max(
        (os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".onnx")),
        key=os.path.getsize,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("labeled", nargs="?", default="labeled.json")
    ap.add_argument("--base", default="google/bert_uncased_L-4_H-256_A-4")
    ap.add_argument("--out", default="model_out")
    ap.add_argument("--epochs", type=float, default=4.0)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--min-confidence", type=float, default=0.85)
    args = ap.parse_args()

    with open(args.labeled) as f:
        rows = [
            r
            for r in json.load(f)
            if r.get("label") is not None
            and r.get("text")
            and r.get("confidence", 1.0) >= args.min_confidence
        ]
    seen, deduped = set(), []
    for r in rows:
        if r["text"] not in seen:
            seen.add(r["text"])
            deduped.append(r)
    positives = sum(int(bool(r["label"])) for r in deduped)
    print(f"{len(deduped)} usable tweets ({positives} farming / {len(deduped) - positives} genuine)")
    if len(deduped) < 200:
        raise SystemExit("need at least 200 labeled tweets, collect more first")
    if positives < 0.05 * len(deduped):
        print("warning: under 5% positives, collect from bait-heavy timelines or lists to balance")

    random.Random(SEED).shuffle(deduped)
    cut = int(len(deduped) * 0.9)
    train_rows, val_rows = deduped[:cut], deduped[cut:]

    # timeline data is ~95% genuine; oversample farming rows in the train split
    # (val stays natural) so the classifier actually learns the rare class
    pos = [r for r in train_rows if r["label"]]
    neg = [r for r in train_rows if not r["label"]]
    if pos:
        factor = max(1, round(len(neg) / len(pos) / 2))  # aim for ~1:2 ratio
        train_rows = neg + pos * factor
        random.Random(SEED + 1).shuffle(train_rows)
        print(f"oversampled {len(pos)} farming rows x{factor} -> {len(train_rows)} train rows")

    tokenizer = AutoTokenizer.from_pretrained(args.base)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base,
        num_labels=2,
        id2label={0: "genuine", 1: "engagement_farming"},
        label2id={"genuine": 0, "engagement_farming": 1},
    )

    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=args.out,
            num_train_epochs=args.epochs,
            per_device_train_batch_size=32,
            per_device_eval_batch_size=64,
            learning_rate=args.lr,
            eval_strategy="epoch",
            save_strategy="no",
            logging_steps=20,
            seed=SEED,
            report_to=[],
        ),
        train_dataset=TweetDataset(train_rows, tokenizer),
        eval_dataset=TweetDataset(val_rows, tokenizer),
        data_collator=DataCollatorWithPadding(tokenizer),
        compute_metrics=metrics,
    )
    trainer.train()
    eval_metrics = trainer.evaluate()
    print("validation:", eval_metrics)

    model.save_pretrained(args.out)
    tokenizer.save_pretrained(args.out)
    with open(os.path.join(args.out, "metrics.json"), "w") as f:
        json.dump(eval_metrics, f, indent=1)

    onnx_dir = os.path.join(args.out, "onnx")
    ORTModelForSequenceClassification.from_pretrained(args.out, export=True).save_pretrained(onnx_dir)

    quant_dir = os.path.join(args.out, "onnx-int8")
    arm = platform.machine() in ("arm64", "aarch64")
    qconfig = (
        AutoQuantizationConfig.arm64(is_static=False)
        if arm
        else AutoQuantizationConfig.avx512_vnni(is_static=False)
    )
    ORTQuantizer.from_pretrained(onnx_dir).quantize(save_dir=quant_dir, quantization_config=qconfig)

    print(f"fp32 ONNX: {os.path.getsize(onnx_path(onnx_dir)) / 1e6:.1f} MB")
    print(f"int8 ONNX: {os.path.getsize(onnx_path(quant_dir)) / 1e6:.1f} MB -> {quant_dir}")


if __name__ == "__main__":
    main()
