"""Small, bounded FFmpeg helpers for future video jobs."""
from pathlib import Path
import subprocess


def transcode_video(source: Path, destination: Path, timeout_seconds: int = 120) -> None:
    """Transcode using a single CPU thread and a safe, broadly supported codec."""
    command = [
        "ffmpeg", "-nostdin", "-y", "-i", str(source), "-threads", "1",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "25", "-an", str(destination),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=timeout_seconds)
    except FileNotFoundError as exc:
        raise RuntimeError("FFmpeg is not installed") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode(errors="replace")[-500:]
        raise RuntimeError(f"FFmpeg failed: {detail}") from exc
