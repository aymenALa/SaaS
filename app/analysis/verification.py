from dataclasses import asdict, dataclass
import cv2
import numpy as np
from app.analysis.hashing import phash, phash_distance, sha256_bytes
from app.analysis.ingestion import ingest_image
from app.analysis.metadata import inspect_metadata
from app.analysis.snapshot import BaselineSnapshot


@dataclass(frozen=True)
class VerificationReport:
    output_sha256: str
    output_size: int
    output_format: str
    output_dimensions: tuple[int, int] | None
    changed_pixel_percentage: float | None
    psnr_db: float | None
    ssim: float | None
    phash: str | None
    phash_distance: int | None
    metadata_diff: dict[str, object]
    alpha_changed: bool | None
    color_information_changed: bool | None
    elapsed_ms: float
    status: str
    message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def verify_output(baseline: BaselineSnapshot, original_image: np.ndarray, output_data: bytes, max_pixels: int) -> VerificationReport:
    import time
    started = time.perf_counter()
    output_image, output_info = ingest_image(output_data, max_pixels)
    output_metadata = inspect_metadata(output_data, output_info.format)
    if output_info.width is None or output_image.size == 0:
        return VerificationReport(sha256_bytes(output_data), len(output_data), output_info.format, None, None, None, None, None, None, {"status": "unavailable"}, None, None, (time.perf_counter() - started) * 1000, output_info.status.value, output_info.message)
    comparable = original_image.shape == output_image.shape
    changed = None; psnr = None; ssim = None
    if comparable:
        left = _to_bgr(original_image); right = _to_bgr(output_image)
        difference = right.astype(np.float32) - left.astype(np.float32)
        changed = float(np.any(difference != 0, axis=2).mean() * 100)
        mse = float(np.mean(difference ** 2))
        psnr = None if mse == 0 else float(20 * np.log10(255.0 / np.sqrt(mse)))
        ssim = _ssim(left, right)
    return VerificationReport(
        sha256_bytes(output_data), len(output_data), output_info.format, (output_info.width, output_info.height), changed, psnr, ssim,
        phash(output_image), phash_distance(baseline.phash, phash(output_image)),
        {"exif": [baseline.metadata.exif, output_metadata.exif], "xmp": [baseline.metadata.xmp, output_metadata.xmp], "iptc": [baseline.metadata.iptc, output_metadata.iptc], "icc_profile": [baseline.metadata.icc_profile, output_metadata.icc_profile]},
        baseline.image_info.alpha_present != output_info.alpha_present, baseline.image_info.color_information != output_info.color_information,
        (time.perf_counter() - started) * 1000, "SUCCESS" if comparable else "PARTIAL", None if comparable else "Pixel comparison unavailable because dimensions changed",
    )


def _ssim(left: np.ndarray, right: np.ndarray) -> float:
    a = cv2.cvtColor(left, cv2.COLOR_BGR2GRAY).astype(np.float64)
    b = cv2.cvtColor(right, cv2.COLOR_BGR2GRAY).astype(np.float64)
    c1, c2 = 6.5025, 58.5225
    mu_a, mu_b = cv2.GaussianBlur(a, (11, 11), 1.5), cv2.GaussianBlur(b, (11, 11), 1.5)
    sigma_a = cv2.GaussianBlur(a * a, (11, 11), 1.5) - mu_a * mu_a
    sigma_b = cv2.GaussianBlur(b * b, (11, 11), 1.5) - mu_b * mu_b
    sigma_ab = cv2.GaussianBlur(a * b, (11, 11), 1.5) - mu_a * mu_b
    score = ((2 * mu_a * mu_b + c1) * (2 * sigma_ab + c2)) / ((mu_a * mu_a + mu_b * mu_b + c1) * (sigma_a + sigma_b + c2))
    return float(np.clip(score.mean(), -1, 1))


def _to_bgr(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image
