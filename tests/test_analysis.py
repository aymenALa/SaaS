import numpy as np
from app.analysis.detectors import OptionalDetector
from app.analysis.pipeline import AnalysisPipeline
from app.analysis.registry import DetectorRegistry
from app.analysis.transformations import RegionTransformer
from app.analysis.types import Detection, DetectorReport, Region


class FixedDetector:
    name = "fixed"
    version = "test-1"
    available = True

    def detect(self, image):
        return DetectorReport(self.name, 0.1, (Detection(self.name, "sample", 1.4, Region(1, 1, 3, 3)),))


def test_registry_and_pipeline_are_selective_and_measurable():
    image = np.full((8, 8, 3), 220, dtype=np.uint8)
    result = AnalysisPipeline(DetectorRegistry([FixedDetector()])).run(image, ["fixed"], "mask")
    assert result.detector_reports[0].detections[0].confidence == 1
    assert result.transform_report.regions_changed == 1
    assert result.elapsed_ms >= 0
    assert result.cpu_ms >= 0
    assert result.peak_memory_kb >= 0


def test_transformations_preserve_source_and_allow_noop():
    source = np.full((8, 8, 3), 220, dtype=np.uint8)
    detection = Detection("fixed", "sample", .8, Region(2, 2, 2, 2))
    transformed, report = RegionTransformer().apply(source, [detection], "mask")
    assert source[2, 2, 0] == 220
    assert transformed[2, 2, 0] != source[2, 2, 0]
    unchanged, noop = RegionTransformer().apply(source, [detection], "leave_unchanged")
    assert np.array_equal(source, unchanged)
    assert noop.pixels_changed == 0


def test_optional_detector_is_explicitly_unavailable_and_non_diagnostic():
    report = OptionalDetector("possible_injury", "not installed", safety_note=True).detect(np.zeros((2, 2, 3), dtype=np.uint8))
    assert report.available is False
    assert "not a medical diagnosis" in report.metadata["disclaimer"]
