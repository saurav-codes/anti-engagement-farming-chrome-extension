import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import onnxruntime as ort
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from huggingface_hub import snapshot_download
from pydantic import BaseModel, Field
from transformers import AutoTokenizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("server")

HF_REPO = "selftaughtdev/engagement-farm-classifier"
THRESHOLD = 0.5
MAX_LENGTH = 128
ONNX_SUBDIR = "onnx-int8"
ONNX_FILE = "model_quantized.onnx"
ALLOW_PATTERNS = [f"{ONNX_SUBDIR}/*", "tokenizer.json", "tokenizer_config.json", "vocab.txt", "special_tokens_map.json", "config.json"]


class Classifier:
    def __init__(self, root):
        start = time.perf_counter()
        onnx_dir = Path(root) / ONNX_SUBDIR
        onnx_file = onnx_dir / ONNX_FILE
        self.session = ort.InferenceSession(str(onnx_file), providers=["CPUExecutionProvider"])
        self.tokenizer = AutoTokenizer.from_pretrained(root)
        config = json.loads((Path(root) / "config.json").read_text())
        self.positive_id = config["label2id"]["engagement_farming"]
        load_ms = (time.perf_counter() - start) * 1000
        logger.info("model ready: dir=%s file=%s in %.1f ms", onnx_dir, ONNX_FILE, load_ms)

    def classify(self, text):
        start = time.perf_counter()
        inputs = self.tokenizer(text, truncation=True, max_length=MAX_LENGTH, return_tensors="np")
        # feed only the inputs the ONNX graph declares (token_type_ids may be absent)
        # cast to int64 because the ONNX graph expects int64 index tensors
        feed = {name: inputs[name].astype("int64") for name in (i.name for i in self.session.get_inputs()) if name in inputs}
        logits = self.session.run(None, feed)[0][0]
        exp = np.exp(logits - logits.max())
        prob = float(exp[self.positive_id] / exp.sum())
        label = "engagement_farming" if prob >= THRESHOLD else "genuine"
        ms = (time.perf_counter() - start) * 1000
        logger.info("classify: text=%r label=%s prob=%.4f ms=%.2f", text[:60], label, prob, ms)
        return {"label": label, "prob": prob, "ms": ms}


@asynccontextmanager
async def lifespan(app):
    env_dir = os.environ.get("MODEL_DIR")
    if env_dir:
        root = Path(env_dir)
        if not root.is_dir():
            raise SystemExit(f"MODEL_DIR not found: {root}")
    else:
        logger.info("downloading serving subset from %s", HF_REPO)
        root = Path(snapshot_download(HF_REPO, allow_patterns=ALLOW_PATTERNS))
    app.state.classifier = Classifier(root)
    yield


class ClassifyIn(BaseModel):
    text: str = Field(max_length=10000)


class ClassifyOut(BaseModel):
    hide: bool
    label: str
    prob: float
    ms: float


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/classify/", response_model=ClassifyOut)
def classify(payload: ClassifyIn):
    text = payload.text.strip()
    if not text:
        raise HTTPException(422, "text must not be empty")
    result = app.state.classifier.classify(text)
    label = result["label"]
    return ClassifyOut(
        hide=label == "engagement_farming",
        label=label,
        prob=round(result["prob"], 4),
        ms=round(result["ms"], 2),
    )
