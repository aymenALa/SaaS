from pathlib import Path
import shutil
import time
from uuid import UUID


def safe_job_path(root: Path, job_id: str, suffix: str) -> Path:
    UUID(job_id)
    return root / f"{job_id}{suffix}"


def cleanup_expired(root: Path, ttl_seconds: int) -> int:
    cutoff = time.time() - ttl_seconds
    removed = 0
    for path in root.iterdir():
        if path.is_file() and path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True); removed += 1
        elif path.is_dir() and path.stat().st_mtime < cutoff:
            shutil.rmtree(path, ignore_errors=True); removed += 1
    return removed
