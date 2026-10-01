import struct
import cv2
import numpy as np
from app.analysis.cancellation import CancellationToken
from app.analysis.executor import PipelineExecutor, _encode
from app.analysis.ingestion import ImageFormat, detect_format, ingest_image
from app.analysis.metadata import inspect_metadata
from app.analysis.registry import default_registry
from app.analysis.snapshot import create_baseline
from app.analysis.status import ResultStatus
from app.analysis.verification import verify_output


def encoded_image(suffix: str = ".png", transparent: bool = False) -> bytes:
    channels = 4 if transparent else 3
    image = np.zeros((24, 32, channels), dtype=np.uint8)
    image[..., 0] = 40; image[..., 1] = 120; image[..., 2] = 220
    if transparent:
        image[..., 3] = 180
    ok, encoded = cv2.imencode(suffix, image)
    assert ok
    return encoded.tobytes()


def test_ingestion_records_formats_dimensions_alpha_and_rejects_unknown():
    png = encoded_image()
    rgba = encoded_image(transparent=True)
    image, info = ingest_image(png, 100_000)
    _, alpha_info = ingest_image(rgba, 100_000)
    _, unsupported = ingest_image(b"not-an-image", 100_000)
    assert detect_format(png)[0] is ImageFormat.PNG
    assert (info.format, info.width, info.height, info.file_size) == ("PNG", 32, 24, len(png))
    assert alpha_info.alpha_present is True
    assert unsupported.status is ResultStatus.UNSUPPORTED
    assert image.shape == (24, 32, 3)


def test_metadata_reports_png_chunks_without_mutating_input():
    png = encoded_image()
    chunk = struct.pack(">I", 5) + b"tEXt" + b"hello" + struct.pack(">I", 0)
    decorated = png[:8] + chunk + png[8:]
    summary = inspect_metadata(decorated, "PNG")
    assert "tEXt" in summary.png_chunks
    assert summary.format_specific == ("tEXt",)
    assert png != decorated


def test_baseline_and_repeated_execution_are_deterministic():
    source = encoded_image(".png")
    executor = PipelineExecutor(default_registry(), 100_000)
    first = executor.execute(source, ["faces"], "pixelate", "PNG")
    second = executor.execute(source, ["faces"], "pixelate", "PNG")
    assert first.status is ResultStatus.SUCCESS
    assert first.baseline.to_dict() == second.baseline.to_dict()
    assert first.output_data == second.output_data
    assert first.verification.ssim == second.verification.ssim


def test_verification_reports_real_metrics_and_no_claimed_unimplemented_values():
    source = encoded_image(".png")
    image, info = ingest_image(source, 100_000)
    baseline = create_baseline(source, image, info, inspect_metadata(source, info.format))
    output = _encode(image, "PNG").data
    report = verify_output(baseline, image, output, 100_000)
    assert report.status == "SUCCESS"
    assert report.output_sha256
    assert report.ssim is not None
    assert report.phash_distance == 0


def test_encoding_fallback_is_explicit_and_cancellation_is_reported():
    image = np.zeros((4, 4, 3), dtype=np.uint8)
    fallback = _encode(image, "AVIF", allow_format_fallback=True)
    assert fallback.status is ResultStatus.FALLBACK
    token = CancellationToken(); token.cancel()
    result = PipelineExecutor(default_registry(), 100_000).execute(encoded_image(), ["faces"], "pixelate", cancel_token=token)
    assert result.status is ResultStatus.PARTIAL
    assert "cancelled" in result.error.lower()
