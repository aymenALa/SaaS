"""Contracts for browser/WASM integrations, without coupling server code to a JS runtime."""
from typing import Protocol


class BrowserDetectorAdapter(Protocol):
    name: str

    async def detect(self, image_bitmap: object) -> list[dict]:
        """Implemented by a Web Worker or WASM detector in the browser."""


WEB_WORKER_GUIDANCE = "Decode once, transfer ImageBitmap/ArrayBuffer to a Worker, return JSON detections, then transform a copy."
