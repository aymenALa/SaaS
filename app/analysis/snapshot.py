from dataclasses import asdict, dataclass
import numpy as np
from app.analysis.hashing import phash, pixel_statistics, sha256_bytes
from app.analysis.ingestion import ImageInfo
from app.analysis.metadata import MetadataSummary


@dataclass(frozen=True)
class BaselineSnapshot:
    sha256: str
    file_size: int
    image_info: ImageInfo
    metadata: MetadataSummary
    pixel_statistics: dict[str, object]
    phash: str

    def to_dict(self) -> dict[str, object]:
        return {"sha256": self.sha256, "file_size": self.file_size, "image_info": self.image_info.to_dict(), "metadata": self.metadata.to_dict(), "pixel_statistics": self.pixel_statistics, "phash": self.phash}


def create_baseline(data: bytes, image: np.ndarray, image_info: ImageInfo, metadata: MetadataSummary) -> BaselineSnapshot:
    return BaselineSnapshot(sha256_bytes(data), len(data), image_info, metadata, pixel_statistics(image), phash(image))
