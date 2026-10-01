from collections.abc import Iterable
from dataclasses import dataclass
import cv2
import numpy as np
from app.analysis.types import Detection, Region


TRANSFORM_NAMES = {"leave_unchanged", "blur", "pixelate", "mask", "crop"}


def clamp_region(region: Region, shape: tuple[int, ...]) -> Region:
    height, width = shape[:2]
    x, y = max(0, region.x), max(0, region.y)
    right, bottom = min(width, region.x + region.width), min(height, region.y + region.height)
    return Region(x, y, max(0, right - x), max(0, bottom - y), region.mask)


@dataclass(frozen=True)
class TransformReport:
    action: str
    regions_changed: int
    pixels_changed: int


class RegionTransformer:
    """Deterministic OpenCV transforms; model-specific transforms can implement the same shape."""

    def __init__(self, mask_color: tuple[int, int, int] = (18, 59, 49)) -> None:
        self.mask_color = mask_color

    def apply(self, image: np.ndarray, detections: Iterable[Detection], action: str) -> tuple[np.ndarray, TransformReport]:
        if action not in TRANSFORM_NAMES:
            raise ValueError(f"Unsupported transformation: {action}")
        output = image.copy()
        detection_list = list(detections)
        if action == "crop":
            regions = [clamp_region(d.region, output.shape) for d in detection_list]
            regions = [r for r in regions if r.width and r.height]
            if not regions:
                return output, TransformReport(action, 0, 0)
            left = min(r.x for r in regions); top = min(r.y for r in regions)
            right = max(r.x + r.width for r in regions); bottom = max(r.y + r.height for r in regions)
            cropped = output[top:bottom, left:right].copy()
            return cropped, TransformReport(action, len(regions), int(cropped.shape[0] * cropped.shape[1]))
        changed = 0
        pixels = 0
        for detection in detection_list:
            region = clamp_region(detection.region, output.shape)
            if region.width == 0 or region.height == 0 or action == "leave_unchanged":
                continue
            before = output[region.y:region.y + region.height, region.x:region.x + region.width].copy()
            roi = before
            if action == "blur":
                kernel = max(3, min(51, (min(region.width, region.height) // 3) * 2 + 1))
                transformed = cv2.GaussianBlur(roi, (kernel, kernel), 0)
            elif action == "pixelate":
                small = cv2.resize(roi, (max(1, region.width // 14), max(1, region.height // 14)), interpolation=cv2.INTER_AREA)
                transformed = cv2.resize(small, (region.width, region.height), interpolation=cv2.INTER_NEAREST)
            elif action == "mask":
                transformed = np.full_like(roi, self.mask_color)
            output[region.y:region.y + region.height, region.x:region.x + region.width] = transformed
            changed += int(np.any(before != transformed, axis=2).sum() > 0)
            pixels += int(np.any(before != transformed, axis=2).sum())
        return output, TransformReport(action, changed, pixels)
