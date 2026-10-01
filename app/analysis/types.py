from dataclasses import dataclass, field
from typing import Any, Protocol
import numpy as np


@dataclass(frozen=True)
class Region:
    """Pixel-space region. Coordinates are clamped by the pipeline before use."""

    x: int
    y: int
    width: int
    height: int
    mask: np.ndarray | None = None

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.width, self.height


@dataclass(frozen=True)
class Detection:
    detector_name: str
    label: str
    confidence: float
    region: Region
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", max(0.0, min(1.0, float(self.confidence))))


@dataclass(frozen=True)
class DetectorReport:
    detector_name: str
    elapsed_ms: float
    detections: tuple[Detection, ...]
    available: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class Detector(Protocol):
    name: str
    version: str
    available: bool

    def detect(self, image: np.ndarray) -> DetectorReport:
        """Analyze an image without mutating it."""
