"""Lightweight primitives for a future video endpoint.

Frames are sampled and tracked with IoU; this avoids running a detector on every frame.
"""
from dataclasses import dataclass


@dataclass
class Track:
    track_id: int
    box: tuple[int, int, int, int]
    missed: int = 0


def iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = a; bx, by, bw, bh = b
    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    overlap = max(0, x2 - x1) * max(0, y2 - y1)
    union = aw * ah + bw * bh - overlap
    return overlap / union if union else 0.0


def update_tracks(tracks: list[Track], detections: list[tuple[int, int, int, int]], next_id: int, threshold: float = .25) -> tuple[list[Track], int]:
    updated: list[Track] = []
    used: set[int] = set()
    for track in tracks:
        matches = [(iou(track.box, box), idx, box) for idx, box in enumerate(detections) if idx not in used]
        if matches and max(matches)[0] >= threshold:
            _, idx, box = max(matches); used.add(idx); updated.append(Track(track.track_id, box))
        elif track.missed < 2:
            updated.append(Track(track.track_id, track.box, track.missed + 1))
    for idx, box in enumerate(detections):
        if idx not in used:
            updated.append(Track(next_id, box)); next_id += 1
    return updated, next_id
