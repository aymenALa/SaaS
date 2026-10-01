import time
import cv2
import numpy as np
from app.analysis.types import Detection, DetectorReport, Region


class FaceDetectorAdapter:
    name = "faces"
    version = "opencv-haar-1"
    available = True

    def __init__(self) -> None:
        cascade = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._classifier = cv2.CascadeClassifier(cascade)

    def detect(self, image: np.ndarray) -> DetectorReport:
        started = time.perf_counter()
        gray = cv2.equalizeHist(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
        found = self._classifier.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(32, 32))
        detections = tuple(Detection(self.name, "face", 0.75, Region(*map(int, box))) for box in found)
        return DetectorReport(self.name, (time.perf_counter() - started) * 1000, detections, metadata={"engine": "opencv"})


class OptionalDetector:
    """Capability placeholder. A real implementation can replace this registry entry."""

    version = "adapter-unavailable-1"
    available = False

    def __init__(self, name: str, reason: str, safety_note: bool = False) -> None:
        self.name, self.reason, self.safety_note = name, reason, safety_note

    def detect(self, image: np.ndarray) -> DetectorReport:
        metadata = {"reason": self.reason}
        if self.safety_note:
            metadata["disclaimer"] = "Assistive visual signal only; not a medical diagnosis."
        return DetectorReport(self.name, 0.0, (), available=False, metadata=metadata)
