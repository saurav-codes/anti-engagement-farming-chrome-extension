import sys

from fastapi.testclient import TestClient

from server import app


def run():
    # context manager so the FastAPI lifespan (model load) runs
    with TestClient(app) as client:
        res = client.post("/api/classify/", json={"text": "Like this if you love pizza"})
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["hide"] is True
        assert body["label"] == "engagement_farming"
        assert body["prob"] >= 0.5
        assert body["ms"] > 0

        res = client.post("/api/classify/", json={"text": "Excited to share my research on climate policy"})
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["hide"] is False
        assert body["label"] == "genuine"

        res = client.post("/api/classify/", json={"text": ""})
        assert res.status_code == 422

        res = client.post("/api/classify/", json=[1, 2])
        assert res.status_code == 422

    return True


try:
    if run():
        print("test_api: all assertions passed")
except AssertionError as exc:
    print(f"test_api: FAILED: {exc}")
    sys.exit(1)
