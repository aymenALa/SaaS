from dataclasses import dataclass
from typing import Protocol
import numpy as np


@dataclass(frozen=True)
class ProtectionResult:
    image: np.ndarray
    backend: str
    device: str


class ProtectionBackend(Protocol):
    name: str

    def protect(self, image: np.ndarray, boxes: list[tuple[int, int, int, int]]) -> ProtectionResult:
        """Return a protected BGR image. Implementations must not mutate input."""


class PixelateBackend:
    """Low-cost, deterministic fallback that does not require model weights."""

    name = "pixelate-cpu"

    def __init__(self, block_size: int = 14) -> None:
        self.block_size = max(4, block_size)

    def protect(self, image: np.ndarray, boxes: list[tuple[int, int, int, int]]) -> ProtectionResult:
        output = image.copy()
        for x, y, w, h in boxes:
            roi = output[y:y + h, x:x + w]
            if roi.size == 0:
                continue
            small_w = max(1, w // self.block_size)
            small_h = max(1, h // self.block_size)
            tiny = cv2_resize(roi, (small_w, small_h))
            output[y:y + h, x:x + w] = cv2_resize(tiny, (w, h), nearest=True)
        return ProtectionResult(output, self.name, "cpu")


def cv2_resize(image: np.ndarray, size: tuple[int, int], nearest: bool = False) -> np.ndarray:
    import cv2
    return cv2.resize(image, size, interpolation=cv2.INTER_NEAREST if nearest else cv2.INTER_AREA)
