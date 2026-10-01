import cv2
import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from app.modules.images import process_image
from app.modules.text import redact_sensitive_text
from app.protection.base import PixelateBackend
from app.protection.model_adapter import ModelProtectionBackend


def jpeg_bytes() -> bytes:
    ok, encoded = cv2.imencode(".jpg", np.full((80, 80, 3), 180, dtype=np.uint8))
    assert ok
    return encoded.tobytes()


def test_image_pipeline_returns_metrics():
    result = process_image(jpeg_bytes(), 100_000, PixelateBackend())
    assert result.image.shape == (80, 80, 3)
    assert result.faces_detected == result.faces_protected
    assert result.backend == "pixelate-cpu"


def test_text_redaction():
    assert "person@example.com" not in redact_sensitive_text("person@example.com, +1 555 555 1234")


def test_model_adapter_validates_contract():
    image = np.zeros((2, 2, 3), dtype=np.uint8)
    adapter = ModelProtectionBackend(lambda value, boxes: value, "research-cpu")
    result = adapter.protect(image, [])
    assert result.backend == "research-cpu"


def test_upload_is_accepted():
    client = TestClient(app)
    response = client.post("/api/v1/jobs", files={"file": ("x.jpg", jpeg_bytes(), "image/jpeg")})
    assert response.status_code == 202
    assert response.json()["status"] in {"queued", "processing", "completed"}
