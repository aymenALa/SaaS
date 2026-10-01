"""Optional adapter seam for PyTorch, ONNX Runtime, or research backends.

The callable owns model loading and device selection. Keeping it outside the API
means heavy weights are opt-in and never downloaded for the CPU fallback.
"""
from collections.abc import Callable
import numpy as np
from app.protection.base import ProtectionResult


class ModelProtectionBackend:
    """Adapt a loaded model function to :class:`ProtectionBackend`.

    ``runner`` receives an image and face boxes and must return a BGR uint8 image.
    It can wrap a Torch ``no_grad`` call, ONNX Runtime session, or StyleAdv
    research pipeline. The service intentionally does not ship research weights.
    """

    def __init__(self, runner: Callable[[np.ndarray, list[tuple[int, int, int, int]]], np.ndarray], name: str, device: str = "cpu") -> None:
        self.runner, self.name, self.device = runner, name, device

    def protect(self, image: np.ndarray, boxes: list[tuple[int, int, int, int]]) -> ProtectionResult:
        output = np.asarray(self.runner(image.copy(), boxes))
        if output.shape != image.shape or output.dtype != np.uint8:
            raise ValueError("Model backend must return a same-shape uint8 BGR image")
        return ProtectionResult(output, self.name, self.device)
