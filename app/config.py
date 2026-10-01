from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    max_upload_bytes: int = 10 * 1024 * 1024
    max_image_pixels: int = 12_000_000
    job_workers: int = 1
    output_ttl_seconds: int = 3600
    temp_dir: Path = Path("./data")
    protection_backend: str = "pixelate"
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", case_sensitive=False)


settings = Settings()
settings.temp_dir.mkdir(parents=True, exist_ok=True)
