from dataclasses import asdict, dataclass
import struct
from app.analysis.ingestion import ImageFormat


@dataclass(frozen=True)
class MetadataSummary:
    exif: bool = False
    xmp: bool = False
    iptc: bool = False
    icc_profile: bool = False
    png_chunks: tuple[str, ...] = ()
    format_specific: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def inspect_metadata(data: bytes, image_format: str | ImageFormat) -> MetadataSummary:
    fmt = str(image_format)
    if fmt == ImageFormat.JPEG.value:
        return _jpeg_metadata(data)
    if fmt == ImageFormat.PNG.value:
        return _png_metadata(data)
    if fmt == ImageFormat.WEBP.value:
        return _webp_metadata(data)
    if fmt == ImageFormat.AVIF.value:
        return MetadataSummary(format_specific=tuple(box for box in ("Exif", "xml ", "colr") if box.encode() in data))
    return MetadataSummary()


def _jpeg_metadata(data: bytes) -> MetadataSummary:
    exif = b"Exif\x00\x00" in data
    xmp = b"http://ns.adobe.com/xap/1.0/" in data or b"<x:xmpmeta" in data
    iptc = b"Photoshop 3.0" in data or b"8BIM" in data
    icc = b"ICC_PROFILE\x00" in data
    return MetadataSummary(exif, xmp, iptc, icc)


def _png_metadata(data: bytes) -> MetadataSummary:
    chunks: list[str] = []
    pos = 8
    while pos + 12 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8].decode("latin1", errors="replace")
        chunks.append(kind)
        pos += 12 + length
        if kind == "IEND":
            break
    return MetadataSummary(
        exif="eXIf" in chunks, xmp="iTXt" in chunks or b"XMP" in data,
        icc_profile="iCCP" in chunks, png_chunks=tuple(chunks),
        format_specific=tuple(chunk for chunk in chunks if chunk in {"tEXt", "zTXt", "iTXt", "pHYs", "sRGB", "gAMA", "cHRM"}),
    )


def _webp_metadata(data: bytes) -> MetadataSummary:
    return MetadataSummary(exif=b"EXIF" in data, xmp=b"XMP " in data, icc_profile=b"ICCP" in data, format_specific=tuple(kind for kind in ("EXIF", "XMP ", "ICCP") if kind.encode() in data))
