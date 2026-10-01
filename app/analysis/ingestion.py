from dataclasses import asdict, dataclass
from enum import StrEnum
import cv2
import numpy as np
from app.analysis.status import ResultStatus


class ImageFormat(StrEnum):
    JPEG = "JPEG"
    PNG = "PNG"
    WEBP = "WEBP"
    AVIF = "AVIF"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ImageInfo:
    status: ResultStatus
    format: str
    mime_type: str | None
    file_size: int
    width: int | None
    height: int | None
    channels: int | None
    alpha_present: bool | None
    color_information: dict[str, object]
    message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self) | {"status": self.status.value}


def detect_format(data: bytes) -> tuple[ImageFormat, str | None]:
    if data.startswith(b"\xff\xd8\xff"):
        return ImageFormat.JPEG, "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ImageFormat.PNG, "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ImageFormat.WEBP, "image/webp"
    if len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in {b"avif", b"avis"}:
        return ImageFormat.AVIF, "image/avif"
    return ImageFormat.UNKNOWN, None


def ingest_image(data: bytes, max_pixels: int) -> tuple[np.ndarray, ImageInfo]:
    image_format, mime_type = detect_format(data)
    if image_format is ImageFormat.UNKNOWN:
        return _unsupported(data, "Unsupported or unrecognized image signature")
    buffer = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_UNCHANGED)
    if image is None:
        return _unsupported(data, f"{image_format.value} is recognized but this decoder cannot read it")
    height, width = image.shape[:2]
    if width * height > max_pixels:
        return image, ImageInfo(ResultStatus.FAILED, image_format.value, mime_type, len(data), width, height, _channels(image), _has_alpha(image), {}, "Image dimensions exceed the configured pixel limit")
    return image, ImageInfo(ResultStatus.SUCCESS, image_format.value, mime_type, len(data), width, height, _channels(image), _has_alpha(image), _color_info(image))


def _unsupported(data: bytes, message: str) -> tuple[np.ndarray, ImageInfo]:
    return np.empty((0, 0, 3), dtype=np.uint8), ImageInfo(ResultStatus.UNSUPPORTED, "UNKNOWN", None, len(data), None, None, None, None, {}, message)


def _channels(image: np.ndarray) -> int:
    return 1 if image.ndim == 2 else int(image.shape[2])


def _has_alpha(image: np.ndarray) -> bool:
    return image.ndim == 3 and image.shape[2] == 4


def _color_info(image: np.ndarray) -> dict[str, object]:
    channels = _channels(image)
    return {"channel_count": channels, "opencv_layout": "BGRA" if channels == 4 else "BGR" if channels == 3 else "GRAY", "dtype": str(image.dtype)}
