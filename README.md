# Privacy Media API

A small Python 3.11+ FastAPI prototype for local-first privacy processing of images. It detects faces with OpenCV and protects them with a CPU-friendly pixelation backend. Processing is deliberately conservative: bounded uploads, one worker by default, no model download at startup, and automatic cleanup of expired files.

The protection backend is an interface. A PyTorch/ONNX adapter, including research integrations inspired by [StyleAdv](https://github.com/minha12/StyleAdv), can be added without changing the API or media pipeline. StyleAdv is research software with substantially higher resource requirements; this prototype does **not** claim universal detector evasion or guarantee protection against any specific recognition system.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` and upload an image to `POST /api/v1/jobs`.

```bash
curl -F "file=@portrait.jpg" http://127.0.0.1:8000/api/v1/jobs
curl http://127.0.0.1:8000/api/v1/jobs/<job_id>
curl -L -o protected.jpg http://127.0.0.1:8000/api/v1/jobs/<job_id>/download
```

## Configuration

Environment variables are intentionally small in scope: `MAX_UPLOAD_BYTES` (default 10 MiB), `MAX_IMAGE_PIXELS` (default 12 MP), `JOB_WORKERS` (default 1), `OUTPUT_TTL_SECONDS` (default 3600), `PROTECTION_BACKEND` (`pixelate` by default), and `TEMP_DIR`.

## Design notes

- `app/modules/images.py` owns image decoding, detection, protection, and quality metrics.
- `app/modules/video.py` contains bounded frame sampling and IoU tracking for a future video endpoint.
- `app/modules/text.py` contains optional privacy-oriented text redaction helpers.
- `app/analysis/` contains the detector registry, standardized detection contracts, composable transformations, benchmarks, and browser/WASM adapter guidance.
- Temporary input/output files are deleted on expiry and on job failure.
- `ffmpeg` is included in the container for future video transcoding; image processing does not invoke it.

## Tests

```bash
pytest -q
```

This is a prototype, not a security certification. Run it behind authentication, rate limits, encrypted storage, and a malware/content scanning layer before exposing it to untrusted public traffic.

## Extending the analysis pipeline

Detectors implement `detect(image) -> DetectorReport`. A report contains the detector name, elapsed time, availability, metadata, and `Detection` objects with a clamped confidence score, pixel-space `Region`, label, and optional mask/metadata. Register a detector with `DetectorRegistry.register()` and request only the required names:

```text
POST /api/v1/jobs
detectors=faces,text
transform=mask
```

Available transformation names are `leave_unchanged`, `blur`, `pixelate`, `mask`, and `crop`. `crop` returns a new canvas around the union of detected regions; if no regions are found it preserves the source dimensions. Optional detector slots report `available=false` instead of pretending to analyze an image. `possible_injury` is explicitly an assistive visual signal only and never a medical diagnosis.

`GET /api/v1/capabilities` exposes the current registry. Browser implementations can use the same result schema from a Web Worker/WASM adapter, then send selected regions to a client-side transformer or to the API. The server pipeline logs elapsed time, CPU time, peak traced memory, detector count, and transform name as structured JSON.

## Reproducible processing stages

The hardening layer now follows this stage order without replacing the existing detector registry or executor:

```text
INPUT → INGESTION → BASELINE SNAPSHOT → ANALYSIS → TRANSFORMATION
      → ENCODING → OUTPUT → VERIFICATION → FINAL REPORT
```

Ingestion is signature-based and records JPEG, PNG, WebP, and AVIF when recognized; a recognized-but-undecodable format is reported as unsupported. Baselines contain immutable SHA-256, pHash, dimensions, alpha/color information, metadata summary, and pixel statistics. Every job manifest records operation names, parameters, status, duration, and failures. Verification reports only metrics that were actually computed, including PSNR, SSIM, pHash distance, changed pixels, metadata differences, and output identity.

No metadata is removed at this stage. No external image-processing library or detector benchmark is included in the hardening phase. The repository currently contains `AnalysisPipeline` and the detector registry; `WorkerRunner`/`InlineRunner` classes were not present in the starting tree, so they were not replaced or silently reimplemented.
