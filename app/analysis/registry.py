from collections.abc import Iterable
from app.analysis.types import Detector


class DetectorRegistry:
    """Explicit plugin registry. Heavy detectors are registered only when enabled."""

    def __init__(self, detectors: Iterable[Detector] = ()) -> None:
        self._detectors: dict[str, Detector] = {}
        for detector in detectors:
            self.register(detector)

    def register(self, detector: Detector) -> None:
        if not detector.name or detector.name in self._detectors:
            raise ValueError(f"Detector name must be unique: {detector.name!r}")
        self._detectors[detector.name] = detector

    def get(self, name: str) -> Detector:
        try:
            return self._detectors[name]
        except KeyError as exc:
            raise KeyError(f"Unknown detector: {name}") from exc

    def select(self, names: Iterable[str]) -> list[Detector]:
        return [self.get(name) for name in names]

    def capabilities(self) -> list[dict[str, object]]:
        return [{"name": d.name, "version": d.version, "available": d.available} for d in self._detectors.values()]


def default_registry() -> DetectorRegistry:
    from app.analysis.detectors import FaceDetectorAdapter, OptionalDetector
    return DetectorRegistry([
        FaceDetectorAdapter(),
        OptionalDetector("hands", "hand/body detector adapter not installed"),
        OptionalDetector("objects", "object detector adapter not installed"),
        OptionalDetector("license_plates", "plate detector adapter not installed"),
        OptionalDetector("text", "OCR adapter not installed"),
        OptionalDetector("documents", "document detector adapter not installed"),
        OptionalDetector("screens", "screen detector adapter not installed"),
        OptionalDetector("logos", "logo detector adapter not installed"),
        OptionalDetector("possible_injury", "assistive visual signal adapter not installed", safety_note=True),
    ])
