from dataclasses import dataclass
from typing import Any
import cv2
import numpy as np
from app.analysis.benchmark import log_benchmark
from app.analysis.cancellation import PipelineCancelled
from app.analysis.ingestion import ImageInfo, ingest_image
from app.analysis.manifest import ProcessingManifest
from app.analysis.metadata import MetadataSummary, inspect_metadata
from app.analysis.pipeline import AnalysisPipeline, PipelineResult
from app.analysis.registry import DetectorRegistry
from app.analysis.snapshot import BaselineSnapshot, create_baseline
from app.analysis.status import ResultStatus
from app.analysis.verification import VerificationReport, verify_output


@dataclass(frozen=True)
class ExecutionResult:
    image: np.ndarray | None
    output_data: bytes | None
    image_info: ImageInfo
    baseline: BaselineSnapshot | None
    pipeline: PipelineResult | None
    verification: VerificationReport | None
    manifest: dict[str, Any]
    status: ResultStatus
    error: str | None = None


@dataclass(frozen=True)
class EncodedOutput:
    data: bytes
    format: str
    status: ResultStatus
    message: str | None = None


class PipelineExecutor:
    """Orchestrates ingestion → baseline → analysis/transformation → encode → verify."""

    def __init__(self, registry: DetectorRegistry, max_pixels: int) -> None:
        self.registry, self.max_pixels = registry, max_pixels

    def execute(self, data: bytes, detector_names: list[str], action: str, output_format: str = "JPEG", cancel_token: object | None = None, allow_format_fallback: bool = False) -> ExecutionResult:
        manifest = ProcessingManifest()
        with manifest.operation("ingestion", {"input_bytes": len(data)}):
            image, image_info = ingest_image(data, self.max_pixels)
        if image_info.status is not ResultStatus.SUCCESS:
            return ExecutionResult(None, None, image_info, None, None, None, manifest.to_dict(), image_info.status, image_info.message)
        with manifest.operation("metadata_inspection", {"mutate": False}):
            metadata = inspect_metadata(data, image_info.format)
        with manifest.operation("baseline_snapshot", {"immutable": True}):
            baseline = create_baseline(data, image, image_info, metadata)
        try:
            _check_cancel(cancel_token)
            with manifest.operation("analysis_and_transformation", {"detectors": detector_names, "transformation": action}):
                pipeline = AnalysisPipeline(self.registry).run(_to_bgr(image), detector_names, action)
            _check_cancel(cancel_token)
            with manifest.operation("encoding", {"format": output_format}):
                encoded = _encode(pipeline.image, output_format, allow_format_fallback)
                if encoded.status is ResultStatus.FALLBACK:
                    manifest.operations[-1].status = ResultStatus.FALLBACK
                    manifest.operations[-1].message = encoded.message
                output_data = encoded.data
            _check_cancel(cancel_token)
            with manifest.operation("verification", {"baseline_sha256": baseline.sha256}):
                verification = verify_output(baseline, _to_bgr(image), output_data, self.max_pixels)
            log_benchmark(pipeline, detector_names, action)
            return ExecutionResult(pipeline.image, output_data, image_info, baseline, pipeline, verification, manifest.to_dict(), ResultStatus.SUCCESS)
        except PipelineCancelled as exc:
            return ExecutionResult(image, None, image_info, baseline, None, None, manifest.to_dict(), ResultStatus.PARTIAL, str(exc))
        except ValueError as exc:
            return ExecutionResult(image, None, image_info, baseline, None, None, manifest.to_dict(), ResultStatus.FAILED, str(exc))
        except Exception as exc:
            return ExecutionResult(image, None, image_info, baseline, None, None, manifest.to_dict(), ResultStatus.FAILED, str(exc))


def _encode(image: np.ndarray, output_format: str, allow_format_fallback: bool = False) -> EncodedOutput:
    formats = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
    requested = output_format.upper()
    suffix = formats.get(requested)
    status = ResultStatus.SUCCESS
    message = None
    if suffix is None and allow_format_fallback:
        suffix = ".png"
        status = ResultStatus.FALLBACK
        message = f"Requested {requested}; encoded as PNG because no encoder is configured"
    if not suffix:
        raise ValueError(f"Unsupported output format: {output_format}")
    params = [cv2.IMWRITE_JPEG_QUALITY, 92] if suffix == ".jpg" else []
    ok, encoded = cv2.imencode(suffix, image, params)
    if not ok:
        raise RuntimeError(f"Could not encode output as {output_format}")
    actual = "JPEG" if suffix == ".jpg" else "PNG" if suffix == ".png" else "WEBP"
    return EncodedOutput(encoded.tobytes(), actual, status, message)


def _check_cancel(token: object | None) -> None:
    if token is not None and getattr(token, "is_set", lambda: False)():
        raise PipelineCancelled("Pipeline cancelled at stage boundary")


def _to_bgr(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image
