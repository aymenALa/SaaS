from dataclasses import dataclass
import time
import tracemalloc
import numpy as np
from app.analysis.registry import DetectorRegistry
from app.analysis.transformations import RegionTransformer, TransformReport
from app.analysis.types import Detection, DetectorReport


@dataclass(frozen=True)
class PipelineResult:
    image: np.ndarray
    detector_reports: tuple[DetectorReport, ...]
    transform_report: TransformReport
    elapsed_ms: float
    cpu_ms: float
    peak_memory_kb: float

    @property
    def detections(self) -> tuple[Detection, ...]:
        return tuple(d for report in self.detector_reports for d in report.detections)


class AnalysisPipeline:
    def __init__(self, registry: DetectorRegistry, transformer: RegionTransformer | None = None) -> None:
        self.registry, self.transformer = registry, transformer or RegionTransformer()

    def run(self, image: np.ndarray, detector_names: list[str], action: str) -> PipelineResult:
        if not detector_names:
            raise ValueError("At least one detector must be selected")
        started, cpu_started = time.perf_counter(), time.process_time()
        tracemalloc.start()
        reports = tuple(self.registry.get(name).detect(image.copy()) for name in detector_names)
        output, transform_report = self.transformer.apply(image, (d for r in reports for d in r.detections), action)
        _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
        return PipelineResult(output, reports, transform_report, (time.perf_counter() - started) * 1000, (time.process_time() - cpu_started) * 1000, peak / 1024)
