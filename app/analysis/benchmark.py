import json
import logging
from app.analysis.pipeline import PipelineResult

logger = logging.getLogger("privacy.analysis")


def log_benchmark(result: PipelineResult, detector_names: list[str], action: str) -> None:
    logger.info(json.dumps({
        "event": "analysis_benchmark", "detectors": detector_names, "transform": action,
        "elapsed_ms": round(result.elapsed_ms, 2), "cpu_ms": round(result.cpu_ms, 2),
        "peak_memory_kb": round(result.peak_memory_kb, 2), "detections": len(result.detections),
    }, sort_keys=True))
