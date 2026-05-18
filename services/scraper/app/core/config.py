"""Scraper service configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Where scraped charts + manifests are written. Shared volume with
    # data-ingestion, which reads from the same path on its own mount.
    data_dir: Path = Path("/app/data/aerodromes")

    # DFS AIP BasicVFR URLs.
    dfs_base_url: str = "https://aip.dfs.de"

    # Polite-scraper delays between page navigations (seconds).
    delay_min: float = 2.0
    delay_max: float = 4.0

    # Default Playwright timeout per page (milliseconds).
    page_timeout_ms: int = 30_000

    # How long a discovered "latest AIRAC edition" stays cached.
    airac_cache_ttl_seconds: int = 3600

    class Config:
        env_file = ".env"


settings = Settings()
