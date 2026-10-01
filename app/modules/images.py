from dataclasses import dataclass
import cv2
import numpy as np
from app.analysis.pipeline import AnalysisPipeline
from app.analysis.registry import default_registry
from app.analysis.types import DetectorReport


@dataclass(frozen=True)
class ImageResult:
    image: np.ndarray
    faces_detected: int
    faces_protected: int
    backend: str
    device: str
    mean_absolute_change: float
    psnr_db: float | None
    detector_reports: tuple[DetectorReport, ...] = ()
    elapsed_ms: float = 0
    cpu_ms: float = 0
    peak_memory_kb: float = 0
    pipeline_result: object | None = None


class FaceDetector:
    def __init__(self) -> None:
        cascade = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._classifier = cv2.CascadeClassifier(cascade)

    def detect(self, image: np.ndarray) -> list[tuple[int, int, int, int]]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        found = self._classifier.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(32, 32))
        return [tuple(map(int, box)) for box in found]


def decode_image(data: bytes, max_pixels: int) -> np.ndarray:
    buffer = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise ValueError("The uploaded file is not a readable image")
    if image.shape[0] * image.shape[1] > max_pixels:
        raise ValueError("Image dimensions exceed the configured pixel limit")
    return image


def process_image(data: bytes, max_pixels: int, backend: object = None, detector: FaceDetector | None = None, detector_names: list[str] | None = None, action: str = "pixelate") -> ImageResult:
    original = decode_image(data, max_pixels)
    registry = default_registry()
    if detector is not None:
        registry = default_registry()
        registry._detectors["faces"] = _LegacyFaceDetector(detector)
    pipeline = AnalysisPipeline(registry)
    result = pipeline.run(original, detector_names or ["faces"], action)
    boxes = [d.region.as_tuple() for d in result.detections]
    # Keep the old model backend seam available for callers that explicitly provide one.
    if backend is not None and detector_names in (None, ["faces"]):
        protected = backend.protect(original, boxes)
        output = protected.image; backend_name, device = protected.backend, protected.device
    else:
        output = result.image; backend_name, device = "opencv-transform-cpu", "cpu"
    delta = np.abs(output.astype(np.float32) - original.astype(np.float32))
    mse = float(np.mean((output.astype(np.float32) - original.astype(np.float32)) ** 2))
    psnr = None if mse == 0 else float(20 * np.log10(255.0 / np.sqrt(mse)))
    return ImageResult(
        output, len(boxes), len(boxes), backend_name, device, float(delta.mean()), psnr,
        result.detector_reports, result.elapsed_ms, result.cpu_ms, result.peak_memory_kb, result,
    )


class _LegacyFaceDetector:
    name, version, available = "faces", "legacy-opencv", True

    def __init__(self, detector: FaceDetector) -> None:
        self.detector = detector

    def detect(self, image: np.ndarray):
        from app.analysis.types import Detection, DetectorReport, Region
        import time
        started = time.perf_counter()
        detections = tuple(Detection(self.name, "face", .75, Region(*box)) for box in self.detector.detect(image))
        return DetectorReport(self.name, (time.perf_counter() - started) * 1000, detections)
