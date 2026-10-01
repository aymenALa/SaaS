import hashlib
import cv2
import numpy as np


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def phash(image: np.ndarray, size: int = 32, low_frequency: int = 8) -> str:
    if image.ndim == 2:
        gray = image
    elif image.shape[2] == 4:
        gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (size, size), interpolation=cv2.INTER_AREA).astype(np.float32)
    coefficients = cv2.dct(resized)[:low_frequency, :low_frequency]
    threshold = float(np.median(coefficients[1:]))
    bits = (coefficients >= threshold).flatten()
    return "".join("1" if bit else "0" for bit in bits)


def phash_distance(left: str | None, right: str | None) -> int | None:
    if not left or not right or len(left) != len(right):
        return None
    return sum(a != b for a, b in zip(left, right))


def pixel_statistics(image: np.ndarray) -> dict[str, object]:
    values = image.astype(np.float32)
    return {"mean": round(float(values.mean()), 5), "std": round(float(values.std()), 5), "min": int(values.min()), "max": int(values.max())}
