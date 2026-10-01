from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4
import cv2
import numpy as np
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.modules.images import FaceDetector, process_image
from app.protection.base import PixelateBackend
from app.analysis.registry import default_registry
from app.analysis.executor import PipelineExecutor
from app.analysis.transformations import TRANSFORM_NAMES
from app.analysis.benchmark import log_benchmark
from app.schemas import Job, JobStatus, Metrics
from app.storage import cleanup_expired, safe_job_path

app = FastAPI(title="Privacy Media API", version="0.1.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
executor = ThreadPoolExecutor(max_workers=max(1, settings.job_workers), thread_name_prefix="privacy-job")
jobs: dict[str, Job] = {}
lock = Lock()
detector = FaceDetector()
backend = PixelateBackend()
registry = default_registry()
pipeline_executor = PipelineExecutor(registry, settings.max_image_pixels)


def now() -> datetime:
    return datetime.now(timezone.utc)


def run_job(job_id: str, data: bytes, filename: str, detector_names: list[str], action: str) -> None:
    input_path = safe_job_path(settings.temp_dir, job_id, ".input")
    output_path = safe_job_path(settings.temp_dir, job_id, ".jpg")
    try:
        input_path.write_bytes(data)
        with lock:
            jobs[job_id].status = JobStatus.processing
        result = pipeline_executor.execute(data, detector_names, action, "JPEG")
        if result.status.value != "SUCCESS" or result.output_data is None:
            raise ValueError(result.error or result.image_info.message or "Processing failed")
        output_path.write_bytes(result.output_data)
        with lock:
            jobs[job_id].status = JobStatus.completed
            jobs[job_id].completed_at = now()
            jobs[job_id].metrics = Metrics(
                faces_detected=sum(len(r.detections) for r in result.pipeline.detector_reports if r.detector_name == "faces"),
                faces_protected=sum(len(r.detections) for r in result.pipeline.detector_reports if r.detector_name == "faces"),
                protected_fraction=(sum(len(r.detections) for r in result.pipeline.detector_reports if r.detector_name == "faces") / max(1, sum(len(r.detections) for r in result.pipeline.detector_reports if r.detector_name == "faces"))),
                mean_absolute_change=round(float(np.abs(result.pipeline.image.astype(np.float32) - cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR).astype(np.float32)).mean()), 3),
                psnr_db=result.verification.psnr_db,
                backend="opencv-transform-cpu", device="cpu",
                detector_reports=[{
                    "detector_name": report.detector_name,
                    "elapsed_ms": round(report.elapsed_ms, 2),
                    "available": report.available,
                    "detections": [{"label": d.label, "confidence": d.confidence, "region": d.region.as_tuple(), "metadata": d.metadata} for d in report.detections],
                    "metadata": report.metadata,
                } for report in result.pipeline.detector_reports],
                transform=action,
                elapsed_ms=round(result.pipeline.elapsed_ms, 2), cpu_ms=round(result.pipeline.cpu_ms, 2), peak_memory_kb=round(result.pipeline.peak_memory_kb, 2),
                baseline=result.baseline.to_dict(), manifest=result.manifest, verification=result.verification.to_dict(),
            )
    except Exception as exc:
        with lock:
            jobs[job_id].status = JobStatus.failed; jobs[job_id].error = str(exc)
        output_path.unlink(missing_ok=True)
    finally:
        input_path.unlink(missing_ok=True)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "backend": backend.name, "device": "cpu"}


@app.get("/api/v1/capabilities")
def capabilities() -> dict[str, object]:
    return {"detectors": registry.capabilities(), "transformations": sorted(TRANSFORM_NAMES)}


@app.get("/", include_in_schema=False)
def home():
    return FileResponse("app/static/index.html")


@app.post("/api/v1/jobs", response_model=Job, status_code=202)
async def create_job(file: UploadFile = File(...), detectors: str = Form("faces"), transform: str = Form("pixelate")) -> Job:
    cleanup_expired(settings.temp_dir, settings.output_ttl_seconds)
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(415, "Only JPEG, PNG, and WebP images are supported")
    detector_names = [name.strip() for name in detectors.split(",") if name.strip()]
    if not detector_names:
        raise HTTPException(400, "Select at least one detector")
    try:
        selected = registry.select(detector_names)
    except KeyError as exc:
        raise HTTPException(400, str(exc)) from exc
    if transform not in TRANSFORM_NAMES:
        raise HTTPException(400, f"Unsupported transformation: {transform}")
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, "File exceeds the configured upload limit")
    job_id = str(uuid4())
    job = Job(id=job_id, status=JobStatus.queued, filename=Path(file.filename or "upload").name, created_at=now())
    with lock:
        jobs[job_id] = job
    executor.submit(run_job, job_id, data, job.filename, detector_names, transform)
    return job


@app.get("/api/v1/jobs/{job_id}", response_model=Job)
def get_job(job_id: str) -> Job:
    with lock:
        job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@app.get("/api/v1/jobs/{job_id}/download")
def download_job(job_id: str):
    job = get_job(job_id)
    if job.status != JobStatus.completed:
        raise HTTPException(409, "Job is not complete")
    output = safe_job_path(settings.temp_dir, job_id, ".jpg")
    if not output.exists():
        raise HTTPException(410, "Output has expired")
    return FileResponse(output, media_type="image/jpeg", filename=f"protected-{Path(job.filename).stem}.jpg")
